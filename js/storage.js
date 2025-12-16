/**
 * Storage 모듈 - 로컬스토리지 데이터 관리
 */
const Storage = {
  KEYS: {
    SCENARIOS: 'trpg_scenarios',
    CHARACTERS: 'trpg_characters',
    CURRENT_GAME: 'trpg_current_game',
    SAVED_GAMES: 'trpg_saved_games',
    SETTINGS: 'trpg_settings'
  },

  // ========== 설정 ==========
  getSettings() {
    return JSON.parse(localStorage.getItem(this.KEYS.SETTINGS) || JSON.stringify({
      imageMode: 'off',  // 'off', 'pollinations', 'gemini'
      imageStyle: 'cinematic digital art'
    }));
  },

  saveSettings(settings) {
    const current = this.getSettings();
    const updated = { ...current, ...settings };
    localStorage.setItem(this.KEYS.SETTINGS, JSON.stringify(updated));
    return updated;
  },

  getImageMode() {
    return this.getSettings().imageMode;
  },

  setImageMode(mode) {
    return this.saveSettings({ imageMode: mode });
  },

  // ========== 시나리오 ==========
  getScenarios() {
    return JSON.parse(localStorage.getItem(this.KEYS.SCENARIOS) || '[]');
  },

  getScenario(id) {
    const scenarios = this.getScenarios();
    return scenarios.find(s => s.id === id);
  },

  saveScenario(scenario) {
    const scenarios = this.getScenarios();
    scenario.id = scenario.id || 'scenario_' + Date.now();
    scenario.created_at = scenario.created_at || new Date().toISOString();
    
    const existingIndex = scenarios.findIndex(s => s.id === scenario.id);
    if (existingIndex >= 0) {
      scenarios[existingIndex] = scenario;
    } else {
      scenarios.push(scenario);
    }
    
    localStorage.setItem(this.KEYS.SCENARIOS, JSON.stringify(scenarios));
    return scenario;
  },

  deleteScenario(id) {
    const scenarios = this.getScenarios().filter(s => s.id !== id);
    localStorage.setItem(this.KEYS.SCENARIOS, JSON.stringify(scenarios));
  },

  // ========== 캐릭터 ==========
  getCharacters() {
    return JSON.parse(localStorage.getItem(this.KEYS.CHARACTERS) || '[]');
  },

  getCharacter(id) {
    const characters = this.getCharacters();
    return characters.find(c => c.id === id);
  },

  saveCharacter(character) {
    const characters = this.getCharacters();
    character.id = character.id || 'char_' + Date.now();
    character.created_at = character.created_at || new Date().toISOString();
    
    const existingIndex = characters.findIndex(c => c.id === character.id);
    if (existingIndex >= 0) {
      characters[existingIndex] = character;
    } else {
      characters.push(character);
    }
    
    localStorage.setItem(this.KEYS.CHARACTERS, JSON.stringify(characters));
    return character;
  },

  deleteCharacter(id) {
    const characters = this.getCharacters().filter(c => c.id !== id);
    localStorage.setItem(this.KEYS.CHARACTERS, JSON.stringify(characters));
  },

  // ========== 현재 게임 ==========
  getCurrentGame() {
    return JSON.parse(localStorage.getItem(this.KEYS.CURRENT_GAME) || 'null');
  },

  saveCurrentGame(game) {
    game.updated_at = new Date().toISOString();
    localStorage.setItem(this.KEYS.CURRENT_GAME, JSON.stringify(game));
    return game;
  },

  clearCurrentGame() {
    localStorage.removeItem(this.KEYS.CURRENT_GAME);
  },

  // 새 게임 시작
  startNewGame(scenarioId, characterId) {
    const scenario = this.getScenario(scenarioId);
    const character = this.getCharacter(characterId);
    
    if (!scenario || !character) {
      throw new Error('시나리오 또는 캐릭터를 찾을 수 없습니다.');
    }

    const game = {
      id: 'game_' + Date.now(),
      scenario_id: scenarioId,
      character_id: characterId,
      scenario: scenario,
      character: { ...character }, // 복사본 (게임 중 변경될 수 있음)
      history: [],
      current_location: scenario.locations?.[0] || '시작 지점',
      danger_level: 'safe',
      started_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    return this.saveCurrentGame(game);
  },

  // 히스토리 추가
  addToHistory(role, text, extra = {}) {
    const game = this.getCurrentGame();
    if (!game) return null;

    game.history.push({
      role,
      text,
      time: new Date().toISOString(),
      ...extra
    });

    return this.saveCurrentGame(game);
  },

  // 캐릭터 상태 업데이트 (HP, 인벤토리 등)
  updateCharacterState(updates) {
    const game = this.getCurrentGame();
    if (!game) return null;

    if (updates.damage) {
      game.character.stats.hp = Math.max(0, game.character.stats.hp - updates.damage);
    }
    if (updates.heal) {
      game.character.stats.hp = Math.min(
        game.character.stats.maxHp,
        game.character.stats.hp + updates.heal
      );
    }
    if (updates.addItems) {
      game.character.inventory = [...game.character.inventory, ...updates.addItems];
    }
    if (updates.removeItems) {
      updates.removeItems.forEach(item => {
        const idx = game.character.inventory.indexOf(item);
        if (idx >= 0) game.character.inventory.splice(idx, 1);
      });
    }
    if (updates.danger_level) {
      game.danger_level = updates.danger_level;
    }

    return this.saveCurrentGame(game);
  },

  // ========== 저장된 게임 ==========
  getSavedGames() {
    return JSON.parse(localStorage.getItem(this.KEYS.SAVED_GAMES) || '[]');
  },

  saveGame(name) {
    const currentGame = this.getCurrentGame();
    if (!currentGame) return null;

    const savedGames = this.getSavedGames();
    const saveData = {
      ...currentGame,
      save_name: name,
      saved_at: new Date().toISOString()
    };

    // 같은 이름이면 덮어쓰기
    const existingIndex = savedGames.findIndex(s => s.save_name === name);
    if (existingIndex >= 0) {
      savedGames[existingIndex] = saveData;
    } else {
      savedGames.push(saveData);
    }

    localStorage.setItem(this.KEYS.SAVED_GAMES, JSON.stringify(savedGames));
    return saveData;
  },

  loadGame(saveId) {
    const savedGames = this.getSavedGames();
    const save = savedGames.find(s => s.id === saveId);
    if (save) {
      return this.saveCurrentGame(save);
    }
    return null;
  },

  deleteSavedGame(saveId) {
    const savedGames = this.getSavedGames().filter(s => s.id !== saveId);
    localStorage.setItem(this.KEYS.SAVED_GAMES, JSON.stringify(savedGames));
  },

  // ========== 유틸리티 ==========
  clearAll() {
    Object.values(this.KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  },

  exportData() {
    const data = {};
    Object.entries(this.KEYS).forEach(([name, key]) => {
      data[name] = localStorage.getItem(key);
    });
    return JSON.stringify(data, null, 2);
  },

  importData(jsonString) {
    try {
      const data = JSON.parse(jsonString);
      Object.entries(this.KEYS).forEach(([name, key]) => {
        if (data[name]) {
          localStorage.setItem(key, data[name]);
        }
      });
      return true;
    } catch (e) {
      console.error('Import failed:', e);
      return false;
    }
  }
};

// 전역으로 사용 가능하게
window.Storage = Storage;
