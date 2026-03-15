from pathlib import Path

from google.adk.cli.fast_api import get_fast_api_app


BASE_DIR = Path(__file__).resolve().parent
AGENTS_DIR = BASE_DIR / "agents"

app = get_fast_api_app(
    agents_dir=str(AGENTS_DIR),
    web=True,
    allow_origins=["*"],
)
