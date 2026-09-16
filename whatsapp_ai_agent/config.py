"""Configuracoes globais da automacao, lidas de variaveis de ambiente."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

# Evolution API (https://github.com/EvolutionAPI/evolution-api) — servidor
# self-hosted de WhatsApp usado no lugar da API oficial da Meta.
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_WEBHOOK_SECRET = os.getenv("EVOLUTION_WEBHOOK_SECRET", "")

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE", str(BASE_DIR / "credentials" / "service_account.json")
)

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "conversas.db"))

CLINICS_DIR = BASE_DIR / "clinics"

PORT = int(os.getenv("PORT", "8000"))
