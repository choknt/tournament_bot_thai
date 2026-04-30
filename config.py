"""
=============================================================
  TOURNAMENT BOT  ·  GLOBAL CONFIGURATION
  Edit values here — no need to dig into other files.
=============================================================
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Credentials (set in .env) ─────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
MONGO_URI: str = os.getenv("MONGO_URI",    "mongodb://localhost:27017")

# ── Hard-coded log channel IDs ────────────────────────────────────────────────
# Channel where completed player registrations are sent
REGISTRATION_LOG_CHANNEL_ID: int = 886855754460
# Channel where staff profile submissions are sent
STAFF_DATA_CHANNEL_ID: int       = 574654650000

# ── Match-card image (Pillow) ─────────────────────────────────────────────────
# Backgrounds are picked randomly. Add/remove paths as needed.
BG_IMAGES: list[str] = [
    "img/bg1.png",
    "img/bg2.png",
    "img/bg3.png",
]

# Font files — place your .ttf fonts in the fonts/ folder.
FONT_BOLD:    str = "fonts/bold.ttf"
FONT_REGULAR: str = "fonts/regular.ttf"

# Card canvas size
CARD_WIDTH:  int = 1280
CARD_HEIGHT: int = 720

# Max pixel size of each element on the card
LOGO_MAX_SIZE:   tuple[int, int] = (220, 220)   # tournament logo (top-centre)
THUMBNAIL_SIZE:  tuple[int, int] = (140, 140)   # small thumbnail (bottom-right)

# Font sizes
VS_FONT_SIZE:   int = 80
TEAM_FONT_SIZE: int = 52
TIME_FONT_SIZE: int = 30

# Darkening overlay alpha (0 = transparent, 255 = black)  
CARD_DARK_ALPHA: int = 110

# ── Embed accent colours (0xRRGGBB) ──────────────────────────────────────────
COLOR_SCHEDULE: int = 0x3498DB   # blue  — schedule
COLOR_RESULTS:  int = 0xE74C3C   # red   — results
COLOR_SUCCESS:  int = 0x2ECC71   # green — success
COLOR_ERROR:    int = 0xE74C3C   # red   — errors
COLOR_INFO:     int = 0x5865F2   # blurple — info / config
COLOR_WARN:     int = 0xF39C12   # orange — warnings
