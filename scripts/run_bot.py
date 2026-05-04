"""Entry point: python scripts/run_bot.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.telegram.bot import run  # noqa: E402

if __name__ == "__main__":
    run()
