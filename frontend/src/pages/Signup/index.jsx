import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import avatarImg from '../../assets/images/avatar.png'
import './Signup.css'

function Signup() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    passwordConfirm: '',
    email: '',
    name: '',
    nickname: '',
    phone: '',
    verificationCode: '',
    birthYear: '',
    birthMonth: '',
    birthDay: '',
    gender: '',
    agreeTerms: false,
    agreePrivacy: false,
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [usernameChecked, setUsernameChecked] = useState(false)
  const [emailVerified, setEmailVerified] = useState(false)
  const [emailCodeSent, setEmailCodeSent] = useState(false)
  const [showTerms, setShowTerms] = useState(false)
  const [showPrivacy, setShowPrivacy] = useState(false)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    })
    if (name === 'username') {
      setUsernameChecked(false)
    }
  }

  const checkUsername = async () => {
    if (!formData.username) {
      alert('아이디를 입력해주세요.')
      return
    }
    // TODO: 실제 중복 확인 API 호출
    alert('사용 가능한 아이디입니다.')
    setUsernameChecked(true)
  }

  const sendVerificationCode = async () => {
    if (!formData.email) {
      alert('이메일을 입력해주세요.')
      return
    }
    try {
      const response = await api.post('/auth/send-verification-email/', { email: formData.email })

      // 개발 환경에서는 인증 코드를 알림으로 표시
      if (response.data.data?.verification_code) {
        alert(`인증번호가 전송되었습니다.\n\n개발 환경 인증 코드: ${response.data.data.verification_code}\n\n(실제 운영에서는 이메일로 전송됩니다)`)
      } else {
        alert('인증번호가 이메일로 전송되었습니다.')
      }

      setEmailCodeSent(true)
    } catch (err) {
      alert(err.response?.data?.message || '인증번호 전송에 실패했습니다.')
    }
  }

  const verifyCode = async () => {
    if (!formData.verificationCode) {
      alert('인증번호를 입력해주세요.')
      return
    }
    try {
      await api.post('/auth/verify-email-code/', {
        email: formData.email,
        code: formData.verificationCode
      })
      alert('이메일 인증이 완료되었습니다.')
      setEmailVerified(true)
    } catch (err) {
      alert(err.response?.data?.message || '인증번호가 올바르지 않습니다.')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // 유효성 검사
    if (!usernameChecked) {
      setError('아이디 중복확인을 해주세요.')
      return
    }

    if (formData.password !== formData.passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }

    if (!emailVerified) {
      setError('이메일 인증을 완료해주세요.')
      return
    }

    if (!formData.agreeTerms || !formData.agreePrivacy) {
      setError('약관에 동의해주세요.')
      return
    }

    setLoading(true)

    try {
      await api.post('/auth/signup/', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        password_confirm: formData.passwordConfirm,
        name: formData.name,
        nickname: formData.nickname,
        phone_number: formData.phone,
        birth_date: formData.birthYear && formData.birthMonth && formData.birthDay
          ? `${formData.birthYear}-${formData.birthMonth.padStart(2, '0')}-${formData.birthDay.padStart(2, '0')}`
          : null,
        gender: formData.gender,
      })

      alert('회원가입이 완료되었습니다. 로그인해주세요.')
      navigate('/login')
    } catch (err) {
      console.error('Signup error:', err)
      setError(
        err.response?.data?.message || '회원가입에 실패했습니다.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="signup-page">
      {/* 헤더 */}
      <header className="signup-header">
        <div className="signup-logo" onClick={() => navigate('/')}>π</div>
        <nav className="signup-nav">
          <button onClick={() => navigate('/app/problems')}>공부하기</button>
          <button onClick={() => navigate('/app/chatbot')}>챗봇</button>
          <button onClick={() => navigate('/app/mypage')}>마이페이지</button>
          <button onClick={() => navigate('/login')}>로그인</button>
        </nav>
      </header>

      {/* 회원가입 폼 */}
      <div className="signup-container">
        <h1 className="signup-title">회원가입</h1>

        {/* 아바타 */}
        <div className="signup-avatar">
          <img src={avatarImg} alt="Avatar" />
          <div className="avatar-badge">사진변경</div>
        </div>

        <form onSubmit={handleSubmit} className="signup-form">
          {error && <div className="error-message">{error}</div>}

          <div className="signup-columns">
            {/* 왼쪽 컬럼 */}
            <div className="signup-column">
              <div className="form-group">
                <label>아이디*</label>
                <div className="input-with-btn">
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    placeholder="* 는 필수항목입니다"
                    required
                  />
                  <button type="button" onClick={checkUsername}>중복확인</button>
                </div>
              </div>

              <div className="form-group">
                <label>비밀번호*</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label>비밀번호 확인*</label>
                <input
                  type="password"
                  name="passwordConfirm"
                  value={formData.passwordConfirm}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label>이메일*</label>
                <div className="input-with-btn">
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                  <button type="button" onClick={sendVerificationCode}>인증번호 전송</button>
                </div>
              </div>

              <div className="form-group">
                <label>인증번호 입력*</label>
                <div className="input-with-btn">
                  <input
                    type="text"
                    name="verificationCode"
                    value={formData.verificationCode}
                    onChange={handleChange}
                    required
                  />
                  <button type="button" onClick={verifyCode}>인증 확인</button>
                </div>
              </div>

              <div className="form-group">
                <label>이름(실명입력)*</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label>닉네임</label>
                <input
                  type="text"
                  name="nickname"
                  value={formData.nickname}
                  onChange={handleChange}
                  placeholder="미기재 시 이름으로 대체"
                />
              </div>
            </div>

            {/* 오른쪽 컬럼 */}
            <div className="signup-column">
              <div className="form-group">
                <label>휴대전화번호(선택사항)</label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="(- 제외)"
                />
              </div>

              <div className="form-group">
                <label>생년월일(선택사항)</label>
                <div className="birth-inputs">
                  <input
                    type="text"
                    name="birthYear"
                    value={formData.birthYear}
                    onChange={handleChange}
                    placeholder="년도"
                  />
                  <input
                    type="text"
                    name="birthMonth"
                    value={formData.birthMonth}
                    onChange={handleChange}
                    placeholder="월"
                  />
                  <input
                    type="text"
                    name="birthDay"
                    value={formData.birthDay}
                    onChange={handleChange}
                    placeholder="일"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>성별(선택사항)</label>
                <div className="gender-options">
                  <label className="checkbox-label">
                    남
                    <input
                      type="radio"
                      name="gender"
                      value="male"
                      checked={formData.gender === 'male'}
                      onChange={handleChange}
                    />
                  </label>
                  <label className="checkbox-label">
                    여
                    <input
                      type="radio"
                      name="gender"
                      value="female"
                      checked={formData.gender === 'female'}
                      onChange={handleChange}
                    />
                  </label>
                </div>
              </div>

              <div className="form-group agreement">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="agreeTerms"
                    checked={formData.agreeTerms}
                    onChange={handleChange}
                  />
                  이용약관 동의
                  <span className="arrow" onClick={() => setShowTerms(true)} style={{ cursor: 'pointer' }}>›</span>
                </label>
              </div>

              <div className="form-group agreement">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="agreePrivacy"
                    checked={formData.agreePrivacy}
                    onChange={handleChange}
                  />
                  개인정보 취급방침 동의
                  <span className="arrow" onClick={() => setShowPrivacy(true)} style={{ cursor: 'pointer' }}>›</span>
                </label>
              </div>
            </div>
          </div>

          <button type="submit" className="signup-submit-btn" disabled={loading}>
            {loading ? '처리중...' : '회원가입'}
          </button>
        </form>
      </div>

      {/* 이용약관 모달 */}
      {showTerms && (
        <div className="modal-overlay" onClick={() => setShowTerms(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>이용약관</h2>
              <button className="modal-close" onClick={() => setShowTerms(false)}>×</button>
            </div>
            <div className="modal-body">
              <h3>제1조 (목적)</h3>
              <p>본 약관은 P[AI] (이하 "서비스")의 이용과 관련하여 회사와 회원 간의 권리, 의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로 합니다.</p>

              <h3>제2조 (용어의 정의)</h3>
              <p>1. "회원"이란 본 약관에 동의하고 서비스에 가입하여 이용하는 자를 말합니다.</p>
              <p>2. "서비스"란 회원이 이용할 수 있는 코딩 테스트 학습 플랫폼을 말합니다.</p>

              <h3>제3조 (서비스의 제공)</h3>
              <p>1. 회사는 다음과 같은 서비스를 제공합니다:</p>
              <ul>
                <li>코딩 테스트 문제 제공 및 풀이</li>
                <li>맞춤형 힌트 시스템</li>
                <li>학습 로드맵 추천</li>
                <li>AI 챗봇을 통한 질의응답</li>
              </ul>

              <h3>제4조 (회원가입)</h3>
              <p>1. 회원가입은 이용자가 약관의 내용에 동의하고 회사가 정한 절차에 따라 신청하여 회사가 승낙함으로써 체결됩니다.</p>
              <p>2. 회원가입 시 제공한 정보의 정확성에 대한 책임은 회원 본인에게 있습니다.</p>

              <h3>제5조 (회원의 의무)</h3>
              <p>1. 회원은 본 약관 및 관계 법령을 준수하여야 합니다.</p>
              <p>2. 회원은 타인의 명예를 훼손하거나 불이익을 주는 행위를 해서는 안 됩니다.</p>
              <p>3. 회원은 서비스를 상업적 목적으로 무단 사용할 수 없습니다.</p>

              <h3>제6조 (서비스의 중단)</h3>
              <p>회사는 시스템 점검, 보수, 교체 등 불가피한 사유가 있는 경우 서비스 제공을 일시적으로 중단할 수 있습니다.</p>
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowTerms(false)}>확인</button>
            </div>
          </div>
        </div>
      )}

      {/* 개인정보 처리방침 모달 */}
      {showPrivacy && (
        <div className="modal-overlay" onClick={() => setShowPrivacy(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>개인정보 처리방침</h2>
              <button className="modal-close" onClick={() => setShowPrivacy(false)}>×</button>
            </div>
            <div className="modal-body">
              <h3>1. 개인정보의 수집 항목 및 이용 목적</h3>
              <p><strong>수집 항목:</strong></p>
              <ul>
                <li>필수: 이메일, 아이디, 비밀번호, 이름</li>
                <li>선택: 닉네임, 전화번호, 생년월일, 성별</li>
              </ul>
              <p><strong>이용 목적:</strong></p>
              <ul>
                <li>회원 식별 및 서비스 제공</li>
                <li>맞춤형 학습 로드맵 제공</li>
                <li>서비스 개선 및 통계 분석</li>
                <li>공지사항 전달</li>
              </ul>

              <h3>2. 개인정보의 보유 및 이용기간</h3>
              <p>회원 탈퇴 시까지 보유하며, 탈퇴 시 지체없이 파기합니다. 단, 관계 법령에 따라 보존할 필요가 있는 경우 해당 기간 동안 보관합니다.</p>

              <h3>3. 개인정보의 제3자 제공</h3>
              <p>회사는 원칙적으로 회원의 개인정보를 제3자에게 제공하지 않습니다. 다만, 법령에 의해 요구되는 경우 예외로 합니다.</p>

              <h3>4. 개인정보의 처리 위탁</h3>
              <p>회사는 원활한 서비스 제공을 위해 개인정보 처리를 외부에 위탁할 수 있으며, 이 경우 사전에 고지합니다.</p>

              <h3>5. 이용자의 권리</h3>
              <p>회원은 언제든지 자신의 개인정보를 조회하거나 수정할 수 있으며, 가입해지(동의 철회)를 요청할 수 있습니다.</p>

              <h3>6. 개인정보의 안전성 확보 조치</h3>
              <p>회사는 개인정보의 안전성 확보를 위해 다음과 같은 조치를 취하고 있습니다:</p>
              <ul>
                <li>비밀번호 암호화 저장</li>
                <li>해킹 등에 대비한 기술적 대책</li>
                <li>개인정보 취급 직원의 최소화 및 교육</li>
              </ul>

              <h3>7. 개인정보 보호책임자</h3>
              <p>회사는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 개인정보 처리와 관련한 정보주체의 불만처리 및 피해구제를 위하여 개인정보 보호책임자를 지정하고 있습니다.</p>
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowPrivacy(false)}>확인</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Signup
