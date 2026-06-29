"""환경 설정 로드."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 경로
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# 모델 (필요 시 .env에서 오버라이드)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# OpenAI 키 확인
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def require_api_key() -> None:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다. .env.example을 .env로 복사하고 키를 넣어주세요."
        )
