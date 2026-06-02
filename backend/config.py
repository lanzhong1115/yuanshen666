from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "fund_manager.db"
HOST = "0.0.0.0"
PORT = 8765
MARKET_REFRESH_SECONDS = 30
CACHE_TTL_SECONDS = {"nav": 3600, "market": 30, "fund_list": 86400}
API_RATE_LIMIT = 2
