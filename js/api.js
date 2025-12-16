/**
 * API 모듈 - 서버와 통신
 */
const API = {
  BASE_URL: 'https://e414bbac-a41e-431a-95c8-37e80ffa48ac-00-1p9b824eqx21u.pike.replit.dev', // 같은 서버에   서 서빙하므로 비워둠

  // 기본 fetch 래퍼
  async request(endpoint, options = {}) {
    const url = this.BASE_URL + endpoint;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || '요청 실패');
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // ========== 시나리오 ==========

  /**
   * 주제를 기반으로 시나리오 생성
   * @param {string} theme - 시나리오 주제
   * @returns {Object} 생성된 시나리오
   */
  async generateScenario(theme) {
    const data = await this.request('/api/scenario/generate', {
      method: 'POST',
      body: JSON.stringify({ theme })
    });
    return data.scenario;
  },

  // ========== 게임 진행 ==========

  /**
   * 플레이어 행동 처리
   * @param {Object} gameState - 현재 게임 상태
   * @param {string} action - 플레이어 행동
   * @returns {Object} GM 응답
   */
  async processAction(gameState, action) {
    const data = await this.request('/api/game/action', {
      method: 'POST',
      body: JSON.stringify({
        scenario: gameState.scenario,
        character: gameState.character,
        history: gameState.history,
        action: action
      })
    });
    return data.result;
  },

  /**
   * 주사위 굴림
   * @param {number} statValue - 스탯 값
   * @param {number} difficulty - 목표 난이도
   * @returns {Object} 주사위 결과
   */
  async rollDice(statValue, difficulty) {
    const data = await this.request('/api/game/roll', {
      method: 'POST',
      body: JSON.stringify({
        stat_value: statValue,
        difficulty: difficulty
      })
    });
    return data;
  },

  /**
   * 주사위 결과에 따른 서술 요청
   * @param {Object} gameState - 현재 게임 상태
   * @param {string} action - 시도한 행동
   * @param {Object} rollResult - 주사위 결과
   * @returns {Object} 결과 서술
   */
  async getRollNarration(gameState, action, rollResult) {
    const data = await this.request('/api/game/roll-result', {
      method: 'POST',
      body: JSON.stringify({
        scenario: gameState.scenario,
        character: gameState.character,
        action: action,
        roll_result: rollResult
      })
    });
    return data.result;
  },

  // ========== 일반 생성 ==========

  /**
   * 일반 텍스트 생성 (프롬프트 직접 전달)
   * @param {string} prompt - 프롬프트
   * @returns {string} 생성된 텍스트
   */
  async generate(prompt) {
    const data = await this.request('/api/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt })
    });
    return data.result;
  },

  // ========== 이미지 생성 ==========

  /**
   * Pollinations.ai로 이미지 URL 생성
   * @param {string} prompt - 이미지 프롬프트 (영어)
   * @returns {string} 이미지 URL
   */
  getPollinationsUrl(prompt) {
    const encoded = encodeURIComponent(prompt);
    return `https://image.pollinations.ai/prompt/${encoded}?width=512&height=512&nologo=true`;
  },

  /**
   * Gemini로 프롬프트 향상 후 이미지 URL 생성
   * @param {string} basicPrompt - 기본 프롬프트
   * @param {string} theme - 시나리오 테마
   * @returns {string} 이미지 URL
   */
  async getGeminiImageUrl(basicPrompt, theme = 'fantasy') {
    try {
      const data = await this.request('/api/image/enhance-prompt', {
        method: 'POST',
        body: JSON.stringify({
          prompt: basicPrompt,
          theme: theme
        })
      });

      const enhancedPrompt = data.enhanced_prompt || basicPrompt;
      return this.getPollinationsUrl(enhancedPrompt);
    } catch (error) {
      // 실패시 기본 Pollinations 사용
      console.error('Gemini enhance failed, using basic prompt:', error);
      return this.getPollinationsUrl(basicPrompt);
    }
  },

  /**
   * 설정에 따라 이미지 URL 생성
   * @param {string} prompt - 이미지 프롬프트
   * @param {string} mode - 'off', 'pollinations', 'gemini'
   * @param {string} theme - 시나리오 테마
   * @returns {string|null} 이미지 URL 또는 null
   */
  async getImageUrl(prompt, mode, theme = 'fantasy') {
    if (!prompt || mode === 'off') {
      return null;
    }

    if (mode === 'gemini') {
      return await this.getGeminiImageUrl(prompt, theme);
    }

    // pollinations (기본)
    return this.getPollinationsUrl(prompt);
  }
};

// 전역으로 사용 가능하게
window.API = API;
