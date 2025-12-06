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
  runpodEndpoint,
  setRunpodEndpoint,
  runpodApiKey,
  setRunpodApiKey,
  hintEngine,
  setHintEngine,
  openaiApiKey,
  setOpenaiApiKey,
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

          <label className={`mode-option ${aiMode === 'runpod' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="aiMode"
              value="runpod"
              checked={aiMode === 'runpod'}
              onChange={(e) => setAiMode(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">Runpod vLLM 방식</div>
              <div className="mode-description">
                Runpod에서 vLLM으로 실행 중인 Qwen 2.5 Coder 32B 모델에 연결합니다. 빠른 추론 속도와 코드 특화 성능을 제공합니다.
              </div>
            </div>
          </label>

          <label className={`mode-option ${aiMode === 'openai' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="aiMode"
              value="openai"
              checked={aiMode === 'openai'}
              onChange={(e) => setAiMode(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">OpenAI API 방식</div>
              <div className="mode-description">
                OpenAI GPT 모델을 사용합니다. GPT-4, GPT-3.5-turbo 등 다양한 모델을 선택할 수 있습니다.
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

      {aiMode === 'runpod' && (
        <div className="section-card">
          <h3>Runpod vLLM 설정</h3>
          <p className="section-description">
            Runpod Workspace에서 실행 중인 vLLM 서버의 엔드포인트 URL을 입력하세요.
          </p>

          <div className="api-key-input">
            <label htmlFor="runpod-endpoint">Runpod Endpoint URL</label>
            <input
              id="runpod-endpoint"
              type="text"
              value={runpodEndpoint}
              onChange={(e) => setRunpodEndpoint(e.target.value)}
              placeholder="https://your-pod-id-8000.proxy.runpod.net"
              className="endpoint-input"
            />
            <small className="input-hint">
              예시: https://abc123def456-8000.proxy.runpod.net (Runpod 대시보드에서 확인)
            </small>
          </div>

          <div className="api-key-input">
            <label htmlFor="runpod-api-key">Runpod API Key (선택사항)</label>
            <input
              id="runpod-api-key"
              type="password"
              value={runpodApiKey}
              onChange={(e) => setRunpodApiKey(e.target.value)}
              placeholder="Runpod API Key (vLLM 서버에 인증이 필요한 경우)"
            />
            <small className="input-hint">
              대부분의 경우 API 키는 불필요합니다. vLLM 서버에 인증이 필요한 경우에만 입력하세요.
            </small>
          </div>

          <div className="runpod-guide">
            <h4>Runpod vLLM 서버 시작 가이드</h4>
            <ol>
              <li>Runpod에서 GPU Pod 생성 (권장: RTX 4090, A6000 이상)</li>
              <li>터미널에서 <code>pip install vllm transformers</code> 실행</li>
              <li><code>runpod_vllm/start_vllm.sh</code> 스크립트 실행</li>
              <li>생성된 엔드포인트 URL을 위 필드에 입력</li>
            </ol>
            <p>
              자세한 가이드는 <code>runpod_vllm/README.md</code> 파일을 참고하세요.
            </p>
          </div>
        </div>
      )}

      {aiMode === 'openai' && (
        <div className="section-card">
          <h3>OpenAI API 설정</h3>
          <p className="section-description">
            OpenAI API 키를 입력하세요. GPT-4, GPT-3.5-turbo 등의 모델을 사용할 수 있습니다.
          </p>

          <div className="api-key-input">
            <label htmlFor="openai-api-key">OpenAI API Key</label>
            <input
              id="openai-api-key"
              type="password"
              placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              value={openaiApiKey}
              onChange={(e) => setOpenaiApiKey(e.target.value)}
            />
            <a
              href="https://platform.openai.com/api-keys"
              target="_blank"
              rel="noopener noreferrer"
              className="get-api-key-link"
            >
              API 키 발급받기
            </a>
          </div>
        </div>
      )}

      {/* 힌트 엔진 선택 섹션 */}
      <div className="section-card">
        <h3>힌트 생성 엔진</h3>
        <p className="section-description">
          힌트 생성 방식을 선택하세요. 모든 사용자에게 동일하게 적용됩니다.
        </p>

        <div className="mode-selector">
          <label className={`mode-option ${hintEngine === 'api' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="hintEngine"
              value="api"
              checked={hintEngine === 'api'}
              onChange={(e) => setHintEngine(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">기존 API 방식</div>
              <div className="mode-description">
                단일 API 호출로 힌트를 생성합니다. 간단하고 빠른 응답을 제공합니다.
              </div>
            </div>
          </label>

          <label className={`mode-option ${hintEngine === 'langgraph' ? 'selected' : ''}`}>
            <input
              type="radio"
              name="hintEngine"
              value="langgraph"
              checked={hintEngine === 'langgraph'}
              onChange={(e) => setHintEngine(e.target.value)}
            />
            <div className="mode-content">
              <div className="mode-title">LangGraph 방식</div>
              <div className="mode-description">
                그래프 기반 워크플로우로 힌트를 생성합니다. 코드 분석, 별점 평가, 취약점 분석 등 단계별 처리로 더 정교한 힌트를 제공합니다.
              </div>
            </div>
          </label>
        </div>
      </div>

      <div className="section-card">
        <h3>AI 모델 선택</h3>
        <p className="section-description">
          힌트 생성에 사용할 AI 모델을 선택하세요. {aiMode === 'openai' ? 'OpenAI GPT 모델을 선택할 수 있습니다.' : '모든 모델은 API 키가 필요하거나 로컬 실행을 권장합니다.'}
        </p>

        <div className="model-selector">
          {aiMode === 'openai' ? (
            <>
              <label className={`mode-option ${modelName === 'gpt-5.1' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="modelName"
                  value="gpt-5.1"
                  checked={modelName === 'gpt-5.1'}
                  onChange={(e) => setModelName(e.target.value)}
                />
                <div className="mode-content">
                  <div className="mode-title">GPT-5.1</div>
                  <div className="mode-description">
                    • OpenAI 최신 플래그십 모델
                    <br/>• 최고 수준의 성능
                    <br/>• 복잡한 추론 능력
                    <br/>• 고난이도 문제에 권장
                  </div>
                </div>
              </label>

              <label className={`mode-option ${modelName === 'gpt-4.1' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="modelName"
                  value="gpt-4.1"
                  checked={modelName === 'gpt-4.1'}
                  onChange={(e) => setModelName(e.target.value)}
                />
                <div className="mode-content">
                  <div className="mode-title">GPT-4.1</div>
                  <div className="mode-description">
                    • GPT-4 시리즈 최신 버전
                    <br/>• 안정적인 고성능
                    <br/>• 코딩 작업에 최적화
                    <br/>• 범용적으로 권장
                  </div>
                </div>
              </label>

              <label className={`mode-option ${modelName === 'o3' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="modelName"
                  value="o3"
                  checked={modelName === 'o3'}
                  onChange={(e) => setModelName(e.target.value)}
                />
                <div className="mode-content">
                  <div className="mode-title">o3</div>
                  <div className="mode-description">
                    • 최신 추론 특화 모델
                    <br/>• 복잡한 코딩 문제 해결
                    <br/>• 깊은 사고 과정
                    <br/>• 어려운 알고리즘에 권장
                  </div>
                </div>
              </label>

              <label className={`mode-option ${modelName === 'gpt-4o' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="modelName"
                  value="gpt-4o"
                  checked={modelName === 'gpt-4o'}
                  onChange={(e) => setModelName(e.target.value)}
                />
                <div className="mode-content">
                  <div className="mode-title">GPT-4o</div>
                  <div className="mode-description">
                    • 멀티모달 지원 모델
                    <br/>• 128K 컨텍스트 윈도우
                    <br/>• 빠르고 비용 효율적
                    <br/>• 일반적인 힌트에 권장
                  </div>
                </div>
              </label>
            </>
          ) : (
            <>
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
            </>
          )}
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
