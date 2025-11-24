import React from 'react'
import './ModelsTab.css'

function ModelsTab({
  aiMode,
  setAiMode,
  apiKey,
  setApiKey,
  modelName,
  setModelName,
  isModelLoaded,
  aiConfigLoading,
  handleUpdateAIConfig,
  handleLoadModel,
  handleUnloadModel
}) {
  return (
    <div className="models-section">
      <div className="section-card">
        <h3>AI 모델 사용 방식</h3>
        <p className="section-description">
          힌트 챗봇에 사용할 AI 모델의 사용 방식을 선택하세요. 모든 사용자에게 적용됩니다.
        </p>

        <div className="mode-selector">
          <label className={`mode-option ${aiMode === 'api' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="aiMode"
              value="api"
              checked={aiMode === 'api'}
              onChange={(e) => setAiMode(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">API 방식 (Hugging Face)</div>
              <div className="mode-description">
                외부 API를 사용하여 모델을 호출합니다. 별도의 GPU 없이 사용 가능하며, 월 30,000회 무료 제공됩니다.
              </div>
            </div>
          </label>

          <label className={`mode-option ${aiMode === 'local' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="aiMode"
              value="local"
              checked={aiMode === 'local'}
              onChange={(e) => setAiMode(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">로컬 로드 방식</div>
              <div className="mode-description">
                모델을 서버 메모리에 로드하여 사용합니다. 고성능 GPU(16GB+ VRAM)가 필요하지만 무제한 사용 가능합니다.
              </div>
            </div>
          </label>
        </div>
      </div>

      {aiMode === 'api' && (
        <div className="section-card">
          <h3>Hugging Face API 키</h3>
          <p className="section-description">
            Hugging Face 계정의 API 키를 입력하세요. 입력한 키는 .env 파일에 저장됩니다.
          </p>

          <div className="api-key-input">
            <input
              type="password"
              placeholder="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <a
              href="https://huggingface.co/settings/tokens"
              target="_blank"
              rel="noopener noreferrer"
              className="get-api-key-link"
            >
              API 키 발급받기
            </a>
          </div>
        </div>
      )}

      {aiMode === 'local' && (
        <div className="section-card">
          <h3>로컬 모델 관리</h3>
          <p className="section-description">
            모델을 메모리에 로드하거나 언로드할 수 있습니다. 로드 완료까지 수 분이 걸릴 수 있습니다.
          </p>

          <div className="model-status">
            <div className="status-item">
              <span className="status-label">모델 상태:</span>
              <span className={`status-value ${isModelLoaded ? 'loaded' : 'unloaded'}`}>
                {isModelLoaded ? '로드됨' : '언로드됨'}
              </span>
            </div>
          </div>

          <div className="model-actions">
            {!isModelLoaded ? (
              <button
                className="load-model-btn"
                onClick={handleLoadModel}
                disabled={aiConfigLoading}
              >
                {aiConfigLoading ? '로드 중...' : '모델 로드'}
              </button>
            ) : (
              <button
                className="unload-model-btn"
                onClick={handleUnloadModel}
                disabled={aiConfigLoading}
              >
                {aiConfigLoading ? '언로드 중...' : '모델 언로드'}
              </button>
            )}
          </div>
        </div>
      )}

      <div className="section-card">
        <h3>AI 모델 선택</h3>
        <p className="section-description">
          힌트 생성에 사용할 AI 모델을 선택하세요. 모든 모델은 API 키가 필요하거나 로컬 실행을 권장합니다.
        </p>

        <div className="model-selector">
          <label className={`mode-option ${modelName === 'meta-llama/Llama-3.2-3B-Instruct' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="modelName"
              value="meta-llama/Llama-3.2-3B-Instruct"
              checked={modelName === 'meta-llama/Llama-3.2-3B-Instruct'}
              onChange={(e) => setModelName(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">Llama 3.2 3B Instruct</div>
              <div className="mode-description">
                • 3B 파라미터 (경량)
                <br/>• API 모드 지원
                <br/>• 빠른 응답 속도
                <br/>• 기본적인 코딩 힌트
              </div>
            </div>
          </label>

          <label className={`mode-option ${modelName === 'Qwen/Qwen2.5-Coder-32B-Instruct' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="modelName"
              value="Qwen/Qwen2.5-Coder-32B-Instruct"
              checked={modelName === 'Qwen/Qwen2.5-Coder-32B-Instruct'}
              onChange={(e) => setModelName(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">Qwen 2.5 Coder 32B</div>
              <div className="mode-description">
                • 32B 파라미터
                <br/>• API 모드 지원
                <br/>• 코딩 특화 모델
                <br/>• 높은 품질의 힌트
              </div>
            </div>
          </label>

          <label className={`mode-option ${modelName === 'mistralai/Mistral-7B-Instruct-v0.3' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="modelName"
              value="mistralai/Mistral-7B-Instruct-v0.3"
              checked={modelName === 'mistralai/Mistral-7B-Instruct-v0.3'}
              onChange={(e) => setModelName(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">Mistral 7B Instruct</div>
              <div className="mode-description">
                • 7B 파라미터
                <br/>• API 모드 지원
                <br/>• 범용 모델
                <br/>• 빠르고 효율적
              </div>
            </div>
          </label>

          <label className={`mode-option ${modelName === 'google/gemma-2-9b-it' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="modelName"
              value="google/gemma-2-9b-it"
              checked={modelName === 'google/gemma-2-9b-it'}
              onChange={(e) => setModelName(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">Gemma 2 9B IT</div>
              <div className="mode-description">
                • 9B 파라미터
                <br/>• API 모드 지원
                <br/>• Google 개발 모델
                <br/>• 균형잡힌 성능
              </div>
            </div>
          </label>

          <label className={`mode-option ${modelName === 'ModelCloud/Brumby-14B-Base-GPTQMODEL-W4A16-v2' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="modelName"
              value="ModelCloud/Brumby-14B-Base-GPTQMODEL-W4A16-v2"
              checked={modelName === 'ModelCloud/Brumby-14B-Base-GPTQMODEL-W4A16-v2'}
              onChange={(e) => setModelName(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">Brumby 14B Base GPTQ</div>
              <div className="mode-description">
                • 14B 파라미터 (GPTQ 양자화)
                <br/>• 로컬 모드 권장
                <br/>• 고품질 응답
                <br/>• 메모리 효율적 (W4A16)
              </div>
            </div>
          </label>
        </div>
      </div>

      <button
        className="save-config-btn"
        onClick={handleUpdateAIConfig}
        disabled={aiConfigLoading}
      >
        {aiConfigLoading ? '저장 중...' : 'AI 설정 저장'}
      </button>
    </div>
  )
}

export default ModelsTab
