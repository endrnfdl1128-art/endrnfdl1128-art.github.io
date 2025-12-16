"""
server.py

AI TRPG 서버
- FastAPI + CORS 설정
- Gemini 2.0 (gemini-2.0-flash-exp) 연동
- 자동 패키지 설치
- GOOGLE_API_KEY 자동/대화형 설정
- TRPG 게임 엔드포인트
"""

import os
import sys
import json
import subprocess
import random
from typing import List, Optional, Dict, Any

# -------------------------------------------------------------------
# 1. 라이브러리 자동 설치
# -------------------------------------------------------------------
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
    from google import genai
    from google.genai import types
except ImportError:
    print("⚠️  필수 라이브러리가 설치되어 있지 않습니다. 자동으로 설치를 시작합니다...")
    required_libraries = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "google-genai",
    ]
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + required_libraries
        )
        print("✅ 라이브러리 설치가 완료되었습니다. 계속해서 서버를 초기화합니다...")
    except Exception as e:
        print(f"❌ 라이브러리 설치 중 오류 발생: {e}")
        raise

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
    from google import genai
    from google.genai import types


# -------------------------------------------------------------------
# 2. API Key 설정 (환경변수 or 터미널 input)
# -------------------------------------------------------------------
API_KEY_ENV_VAR = "GOOGLE_API_KEY"

api_key = os.environ.get(API_KEY_ENV_VAR)
if not api_key:
    # GEMINI_API_KEY도 확인
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("⚠️  GOOGLE_API_KEY 환경 변수가 설정되어 있지 않습니다.")
    api_key = input("👉 Gemini API 키를 입력하세요: ").strip()
    if not api_key:
        raise RuntimeError("❌ GOOGLE_API_KEY가 설정되지 않아 서버를 시작할 수 없습니다.")
    os.environ[API_KEY_ENV_VAR] = api_key

# google-genai 클라이언트 생성
client = genai.Client(api_key=api_key)


# -------------------------------------------------------------------
# 3. FastAPI 앱 및 CORS 설정
# -------------------------------------------------------------------
app = FastAPI(
    title="AI TRPG Server",
    description="Gemini 2.0 기반 AI TRPG 게임 서버",
    version="2.0.0",
)

# CORS: GitHub Pages 도메인 명시적 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://endrnfdl1128-art.github.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# 4. 요청/응답 스키마 정의 (Pydantic)
# -------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str


class ScenarioRequest(BaseModel):
    theme: str


class GameActionRequest(BaseModel):
    scenario: Dict[str, Any]
    character: Dict[str, Any]
    history: List[Dict[str, str]]
    action: str


class RollRequest(BaseModel):
    stat_value: int = 10
    difficulty: int = 12


class RollResultRequest(BaseModel):
    scenario: Dict[str, Any]
    character: Dict[str, Any]
    action: str
    roll_result: Dict[str, Any]


class ImagePromptRequest(BaseModel):
    prompt: str
    theme: Optional[str] = "fantasy"


class GenerateImagePromptRequest(BaseModel):
    scene: str
    scenario: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------------
# 5. 유틸리티 함수
# -------------------------------------------------------------------
def call_gemini(prompt: str, system_instruction: str = "", use_json_mode: bool = True, temperature: float = 0.7) -> str:
    """
    Gemini 2.0 호출 헬퍼 함수
    """
    try:
        config_params = {
            "temperature": temperature,
        }
        
        if use_json_mode:
            config_params["response_mime_type"] = "application/json"
        
        if system_instruction:
            config_params["system_instruction"] = system_instruction
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(**config_params),
        )
        
        if not hasattr(response, "text"):
            raise ValueError("Gemini 응답에 text 속성이 없습니다.")
        
        return response.text
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Gemini 호출 중 오류가 발생했습니다.", "reason": str(e)}
        )


def parse_json_response(text: str) -> Dict[str, Any]:
    """
    JSON 응답 파싱
    """
    try:
        parsed = json.loads(text)
        
        # 배열이면 dict로 감싸기
        if isinstance(parsed, list):
            parsed = {"items": parsed}
        
        if not isinstance(parsed, dict):
            parsed = {"result": parsed}
        
        return parsed
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "AI 응답(JSON) 파싱에 실패했습니다.",
                "reason": str(e),
                "raw_response": text,
            }
        )


# -------------------------------------------------------------------
# 6. 정적 파일 서빙
# -------------------------------------------------------------------
@app.get("/")
def index():
    """메인 페이지"""
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"status": "ok", "message": "AI TRPG Server is running.", "model": "gemini-2.0-flash-exp"}


# frontend 폴더가 있으면 정적 파일 서빙
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# -------------------------------------------------------------------
# 7. API 엔드포인트
# -------------------------------------------------------------------

@app.post("/api/generate")
def generate(request: GenerateRequest) -> Dict[str, Any]:
    """일반 텍스트 생성"""
    try:
        response_text = call_gemini(request.prompt, use_json_mode=False)
        return {"success": True, "result": response_text}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/scenario/generate")
def generate_scenario(request: ScenarioRequest) -> Dict[str, Any]:
    """시나리오 생성"""
    system_instruction = """당신은 TRPG 시나리오 작가입니다.
사용자가 제공한 주제를 바탕으로 흥미진진한 TRPG 시나리오를 생성합니다.

출력은 반드시 다음 JSON 형식이어야 합니다:
{
  "title": "시나리오 제목 (한글)",
  "setting": "세계관 설명 2-3문장",
  "goal": "플레이어의 최종 목표",
  "starting_scene": "게임 시작 시 첫 장면 묘사 (3-4문장, 생생하게)",
  "locations": ["장소1", "장소2", "장소3", "장소4", "장소5"],
  "npcs": [
    {"name": "NPC이름1", "role": "역할", "personality": "성격 특징"},
    {"name": "NPC이름2", "role": "역할", "personality": "성격 특징"},
    {"name": "NPC이름3", "role": "역할", "personality": "성격 특징"}
  ],
  "threats": ["위협요소1", "위협요소2", "위협요소3"],
  "items": ["획득가능 아이템1", "아이템2", "아이템3", "아이템4", "아이템5"]
}"""

    prompt = f"주제: {request.theme}\n\n위 주제로 TRPG 시나리오를 생성해주세요."
    
    try:
        response_text = call_gemini(prompt, system_instruction, use_json_mode=True)
        scenario = parse_json_response(response_text)
        return {"success": True, "scenario": scenario}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/game/action")
def game_action(request: GameActionRequest) -> Dict[str, Any]:
    """플레이어 행동 처리 및 GM 응답"""
    scenario = request.scenario
    character = request.character
    history = request.history
    action = request.action
    
    # 최근 히스토리만 사용 (토큰 절약)
    recent_history = history[-10:] if len(history) > 10 else history
    history_text = '\n'.join([
        f"{'[GM]' if h['role'] == 'gm' else '[플레이어]' if h['role'] == 'player' else '[NPC]' if h['role'] == 'npc' else '[시스템]'}: {h['text']}" 
        for h in recent_history
    ])
    
    system_instruction = """당신은 TRPG 게임 마스터입니다. 몰입감 있게 진행하세요.

중요: 
1. 플레이어의 행동을 다시 묘사하거나 반복하지 마세요. (이미 플레이어가 입력했습니다)
2. 오직 행동에 대한 '결과', 'NPC의 반응', '변화된 상황'만 묘사하세요.
3. 상황 묘사(narration)와 NPC의 대사(dialogues)를 반드시 분리해야 합니다.

[이미지 프롬프트 작성 규칙]
- 반드시 영어로 작성하세요.
- 시나리오의 시대적 배경(예: medieval fantasy, cyberpunk, horror)을 가장 앞에 명시하세요.
- 화풍 키워드 필수 포함: "cinematic lighting, highly detailed, atmospheric, 8k, digital art"
- 인물 묘사가 필요하면 "anime style" 또는 "realistic style" 중 하나를 일관되게 사용하세요.

출력은 반드시 다음 JSON 형식이어야 합니다:
{
  "narration": "행동의 결과와 상황 변화 (3-5문장, 플레이어 행동 반복 금지)",
  "dialogues": [
    {"speaker": "NPC이름", "text": "NPC의 대사 내용"},
    {"speaker": "NPC이름2", "text": "NPC2의 대사 내용"}
  ],
  "requires_roll": true 또는 false,
  "roll_type": "판정이 필요한 경우 스탯 이름 (strength/agility/intelligence/luck), 필요없으면 null",
  "roll_difficulty": "판정 난이도 숫자 (8-18 사이), 필요없으면 null",
  "damage_taken": "플레이어가 받은 피해 (없으면 0)",
  "items_gained": ["획득한 아이템들"],
  "items_lost": ["잃어버린 아이템들"],
  "npc_present": "현재 장면에 등장한 NPC 이름 또는 null",
  "danger_level": "safe/caution/danger 중 하나",
  "image_prompt": "시대 배경 + 현재 장면 묘사 + 화풍 키워드 (영어로 작성)"
}"""

    prompt = f"""[시나리오 정보]
제목: {scenario.get('title', '')}
배경: {scenario.get('setting', '')}
목표: {scenario.get('goal', '')}
장소들: {', '.join(scenario.get('locations', []))}
위협요소: {', '.join(scenario.get('threats', []))}

[NPC 정보]
{json.dumps(scenario.get('npcs', []), ensure_ascii=False)}

[플레이어 캐릭터]
이름: {character.get('name', '')}
직업: {character.get('class', '')}
HP: {character.get('stats', {}).get('hp', 100)}/{character.get('stats', {}).get('maxHp', 100)}
힘: {character.get('stats', {}).get('strength', 10)} / 민첩: {character.get('stats', {}).get('agility', 10)} / 지능: {character.get('stats', {}).get('intelligence', 10)} / 행운: {character.get('stats', {}).get('luck', 10)}
소지품: {', '.join(character.get('inventory', []))}
배경: {character.get('background', '')}

[최근 진행 상황]
{history_text}

[플레이어 행동]
{action}

(위 행동에 대한 결과만 묘사하세요. 행동 자체를 복창하지 마세요.)"""

    try:
        response_text = call_gemini(prompt, system_instruction, use_json_mode=True)
        result = parse_json_response(response_text)
        
        # dialogues 필드가 없을 경우 빈 리스트로 초기화
        if 'dialogues' not in result:
            result['dialogues'] = []
            
        return {"success": True, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        # 파싱 실패시 기본 응답
        return {
            "success": True,
            "result": {
                "narration": "알 수 없는 오류가 발생했습니다.",
                "dialogues": [],
                "requires_roll": False,
                "roll_type": None,
                "roll_difficulty": None,
                "damage_taken": 0,
                "items_gained": [],
                "items_lost": [],
                "npc_present": None,
                "danger_level": "safe",
                "image_prompt": None
            }
        }


@app.post("/api/game/roll")
def roll_dice(request: RollRequest) -> Dict[str, Any]:
    """주사위 판정 처리"""
    try:
        stat_value = request.stat_value
        difficulty = request.difficulty
        
        roll = random.randint(1, 20)
        total = roll + (stat_value - 10) // 2  # 스탯 보너스
        success = total >= difficulty
        
        # 크리티컬 / 펌블
        critical = roll == 20
        fumble = roll == 1
        
        return {
            "success": True,
            "roll": roll,
            "bonus": (stat_value - 10) // 2,
            "total": total,
            "difficulty": difficulty,
            "is_success": success or critical,
            "is_critical": critical,
            "is_fumble": fumble
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/game/roll-result")
def roll_result_narration(request: RollResultRequest) -> Dict[str, Any]:
    """주사위 결과에 따른 서술"""
    scenario = request.scenario
    character = request.character
    action = request.action
    roll_result = request.roll_result
    
    success_text = "대성공!" if roll_result.get('is_critical') else "성공!" if roll_result.get('is_success') else "대실패..." if roll_result.get('is_fumble') else "실패..."
    
    system_instruction = """당신은 TRPG 게임 마스터입니다.

중요: 플레이어의 행동을 반복 서술하지 마세요. 판정 결과에 따른 '결과'만 묘사하세요.

[이미지 프롬프트 작성 규칙]
- 반드시 영어로 작성하세요.
- 시나리오의 시대적 배경(예: medieval fantasy)을 포함하세요.
- 화풍 키워드 필수: "cinematic lighting, highly detailed, atmospheric, 8k"

출력은 반드시 다음 JSON 형식이어야 합니다:
{
  "narration": "결과 묘사 (2-4문장, NPC 대사 제외, 행동 반복 금지)",
  "dialogues": [
    {"speaker": "NPC이름", "text": "NPC의 대사 내용"}
  ],
  "damage_taken": "실패로 인한 피해 (0-20)",
  "items_gained": ["성공시 획득 아이템"],
  "danger_level": "safe/caution/danger",
  "image_prompt": "시대 배경 + 현재 장면 묘사 + 화풍 키워드 (영어로 작성)"
}"""

    prompt = f"""플레이어가 "{action}" 행동을 시도했고, 주사위 판정 결과는 [{success_text}]입니다.
주사위: {roll_result.get('roll')} + 보너스 {roll_result.get('bonus')} = {roll_result.get('total')} (목표: {roll_result.get('difficulty')})

캐릭터: {character.get('name')} ({character.get('class')})

판정 결과에 맞는 상황 묘사를 생성해주세요."""

    try:
        response_text = call_gemini(prompt, system_instruction, use_json_mode=True)
        result = parse_json_response(response_text)
        
        if 'dialogues' not in result:
            result['dialogues'] = []
            
        return {"success": True, "result": result}
    except:
        return {
            "success": True,
            "result": {
                "narration": "판정 결과가 적용되었습니다.",
                "dialogues": [],
                "damage_taken": 0,
                "items_gained": [],
                "danger_level": "safe",
                "image_prompt": None
            }
        }


@app.post("/api/image/enhance-prompt")
def enhance_image_prompt(request: ImagePromptRequest) -> Dict[str, Any]:
    """Gemini로 이미지 프롬프트 향상 (더 상세하고 예술적으로)"""
    system_instruction = """You are an expert at writing image generation prompts.
Convert basic scene descriptions into detailed, artistic image prompts.

Include:
- Art style (e.g., digital art, oil painting, cinematic, anime)
- Lighting and atmosphere
- Color palette
- Composition details
- Mood and emotion

Respond with ONLY the enhanced prompt, no explanations. Keep it under 200 words."""

    prompt = f"""Basic description: {request.prompt}
Theme/Genre: {request.theme}

Create a detailed image generation prompt."""

    try:
        response_text = call_gemini(prompt, system_instruction, use_json_mode=False)
        return {"success": True, "enhanced_prompt": response_text.strip()}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "enhanced_prompt": request.prompt
        }


@app.post("/api/image/generate-prompt")
def generate_image_prompt(request: GenerateImagePromptRequest) -> Dict[str, Any]:
    """장면 설명으로부터 이미지 프롬프트 생성"""
    scenario = request.scenario or {}
    
    system_instruction = """Create an image generation prompt for this TRPG scene.

Write a detailed image prompt in English (under 150 words) that captures:
- The environment and location
- Lighting and atmosphere
- Key visual elements
- Mood (tense, peaceful, mysterious, etc.)

Style: cinematic digital art, dramatic lighting

Respond with ONLY the prompt, nothing else."""

    prompt = f"""Scene: {request.scene}
Setting: {scenario.get('setting', 'fantasy world')}
Theme: {scenario.get('theme', 'adventure')}

Create an image generation prompt."""

    try:
        response_text = call_gemini(prompt, system_instruction, use_json_mode=False)
        return {"success": True, "image_prompt": response_text.strip()}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# -------------------------------------------------------------------
# 8. 테스트 엔드포인트
# -------------------------------------------------------------------

@app.get("/api/test/health")
def test_health() -> Dict[str, Any]:
    """서버 상태 확인"""
    return {
        "success": True,
        "status": "healthy",
        "message": "AI TRPG 서버가 정상 작동 중입니다",
        "model": "gemini-2.0-flash-exp",
        "endpoints": {
            "scenario": "/api/scenario/generate",
            "game_action": "/api/game/action",
            "roll": "/api/game/roll",
            "roll_result": "/api/game/roll-result",
            "image_enhance": "/api/image/enhance-prompt",
            "image_generate": "/api/image/generate-prompt"
        }
    }


@app.get("/api/test/gemini")
def test_gemini() -> Dict[str, Any]:
    """Gemini API 연결 테스트"""
    try:
        response_text = call_gemini("안녕하세요! 간단히 인사해주세요.", use_json_mode=False)
        return {
            "success": True,
            "message": "Gemini API 연결 성공",
            "api_key_configured": True,
            "response": response_text
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Gemini API 연결 실패",
                "error": str(e),
                "api_key_configured": False
            }
        )


@app.get("/api/test/scenario")
def test_scenario() -> Dict[str, Any]:
    """시나리오 생성 테스트 (샘플 데이터)"""
    try:
        request = ScenarioRequest(theme="좀비 아포칼립스")
        result = generate_scenario(request)
        result["message"] = "시나리오 생성 테스트 성공"
        result["theme"] = request.theme
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "시나리오 생성 테스트 실패",
                "error": str(e)
            }
        )


@app.get("/api/test/action")
def test_action() -> Dict[str, Any]:
    """게임 액션 테스트 (샘플 데이터)"""
    sample_scenario = {
        'title': '테스트 던전',
        'setting': '어두운 던전',
        'goal': '보물 찾기',
        'locations': ['입구', '복도', '보물방'],
        'threats': ['함정', '몬스터'],
        'npcs': [{'name': '가이드', 'role': '조력자', 'personality': '친절함'}]
    }
    
    sample_character = {
        'name': '테스트 영웅',
        'class': '전사',
        'stats': {
            'hp': 80,
            'maxHp': 100,
            'strength': 15,
            'agility': 12,
            'intelligence': 10,
            'luck': 8
        },
        'inventory': ['검', '횃불'],
        'background': '용감한 모험가'
    }
    
    try:
        request = GameActionRequest(
            scenario=sample_scenario,
            character=sample_character,
            history=[],
            action="앞으로 조심스럽게 걸어간다"
        )
        result = game_action(request)
        result["message"] = "게임 액션 테스트 성공"
        result["test_data"] = {
            "scenario": sample_scenario,
            "character": sample_character,
            "action": request.action
        }
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "게임 액션 테스트 실패",
                "error": str(e)
            }
        )


@app.get("/api/test/roll")
def test_roll() -> Dict[str, Any]:
    """주사위 굴림 테스트"""
    stat_value = 14
    difficulty = 12
    
    request = RollRequest(stat_value=stat_value, difficulty=difficulty)
    result = roll_dice(request)
    
    interpretation = (
        '크리티컬!' if result.get('is_critical') else
        '펌블...' if result.get('is_fumble') else
        '성공!' if result.get('is_success') else
        '실패'
    )
    
    result["message"] = "주사위 굴림 테스트"
    result["test_params"] = {
        "stat_value": stat_value,
        "difficulty": difficulty
    }
    result["interpretation"] = interpretation
    
    return result


@app.get("/api/test/all")
def test_all() -> Dict[str, Any]:
    """모든 기능 종합 테스트"""
    import datetime
    
    results = {
        'server': {'status': 'unknown'},
        'gemini': {'status': 'unknown'},
        'roll': {'status': 'unknown'}
    }
    
    # 서버 상태
    results['server'] = {
        'status': 'ok',
        'message': '서버 정상 작동'
    }
    
    # Gemini API
    try:
        call_gemini("테스트", use_json_mode=False)
        results['gemini'] = {
            'status': 'ok',
            'message': 'Gemini API 연결 성공',
            'api_key_configured': True
        }
    except Exception as e:
        results['gemini'] = {
            'status': 'error',
            'message': str(e)
        }
    
    # 주사위 굴림
    roll = random.randint(1, 20)
    results['roll'] = {
        'status': 'ok',
        'message': f'주사위 굴림 성공: {roll}'
    }
    
    # 전체 상태
    all_ok = all(r['status'] == 'ok' for r in results.values())
    
    return {
        'success': all_ok,
        'message': '모든 테스트 통과' if all_ok else '일부 테스트 실패',
        'results': results,
        'timestamp': datetime.datetime.now().isoformat()
    }


# -------------------------------------------------------------------
# 9. 단독 실행 시: uvicorn으로 서버 실행
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("🎮 AI TRPG 서버 시작!")
    print("📍 http://localhost:8000 에서 접속하세요")
    print("📚 API 문서: http://localhost:8000/docs")
    print("")
    print("📋 테스트 엔드포인트:")
    print("  GET  /api/test/health   - 서버 상태 확인")
    print("  GET  /api/test/gemini   - Gemini API 테스트")
    print("  GET  /api/test/scenario - 시나리오 생성 테스트")
    print("  GET  /api/test/action   - 게임 액션 테스트")
    print("  GET  /api/test/roll     - 주사위 굴림 테스트")
    print("  GET  /api/test/all      - 전체 기능 테스트")
    print("=" * 50)
    
    # app 객체를 직접 전달 (모듈 임포트 오류 방지)
    uvicorn.run(app, host="0.0.0.0", port=8000)
