"""
utils/image_gen.py
Generates the match-card PNG using Pillow.

Card layout
───────────────────────────────────────
  [          TOUR LOGO          ]   ← top-centre
  [                             ]
  [  Team1     VS     Team2     ]   ← centre
  [                             ]
  [       DD/MM/YYYY HH:MM      ]   ← bottom-centre  [THUMB]
───────────────────────────────────────
Background is a random file from config.BG_IMAGES (darkened for readability).
Tour logo and thumbnail are fetched from URLs / Discord CDN.
"""

from __future__ import annotations

import io
import random
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont

import config as cfg


# ── Image download ────────────────────────────────────────────────────────────

async def _fetch_image(url: str) -> Image.Image | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None
    return None


# ── Font loader ───────────────────────────────────────────────────────────────

def _font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        # Fallback to PIL built-in if fonts not found
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()


# ── Paste helpers ─────────────────────────────────────────────────────────────

def _paste_centre_x(canvas: Image.Image, layer: Image.Image, y: int) -> None:
    x = (canvas.width - layer.width) // 2
    if layer.mode == "RGBA":
        canvas.paste(layer, (x, y), layer)
    else:
        canvas.paste(layer, (x, y))


def _paste_bottom_right(canvas: Image.Image, layer: Image.Image, margin: int = 24) -> None:
    x = canvas.width  - layer.width  - margin
    y = canvas.height - layer.height - margin
    if layer.mode == "RGBA":
        canvas.paste(layer, (x, y), layer)
    else:
        canvas.paste(layer, (x, y))


# ── Text helpers ──────────────────────────────────────────────────────────────

def _text_size(draw: ImageDraw.ImageDraw, text: str,
               font: ImageFont.ImageFont) -> tuple[int, int]:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


# ── Main generator ────────────────────────────────────────────────────────────

async def generate_match_card(
    team1: str,
    team2: str,
    time_str: str,
    logo_url: str | None = None,
    thumbnail_url: str | None = None,
) -> io.BytesIO:
    """
    Generate and return a PNG match card as a BytesIO object.

    Args:
        team1:         Captain/team name (left side)
        team2:         Captain/team name (right side)
        time_str:      Human-readable UTC time string for the bottom bar
        logo_url:      URL of the tournament logo image
        thumbnail_url: URL of the small thumbnail image (bottom-right)
    """
    W, H = cfg.CARD_WIDTH, cfg.CARD_HEIGHT

    # ── Background ─────────────────────────────────────────────────────────────
    bg_path = random.choice(cfg.BG_IMAGES)
    try:
        bg = Image.open(bg_path).convert("RGBA").resize((W, H), Image.LANCZOS)
    except FileNotFoundError:
        bg = Image.new("RGBA", (W, H), (15, 15, 25, 255))

    # Darken for readability
    dark = Image.new("RGBA", (W, H), (0, 0, 0, cfg.CARD_DARK_ALPHA))
    bg = Image.alpha_composite(bg, dark)

    draw = ImageDraw.Draw(bg)

    font_team = _font(cfg.FONT_BOLD,    cfg.TEAM_FONT_SIZE)
    font_vs   = _font(cfg.FONT_BOLD,    cfg.VS_FONT_SIZE)
    font_time = _font(cfg.FONT_REGULAR, cfg.TIME_FONT_SIZE)

    # ── Tournament logo (top-centre) ───────────────────────────────────────────
    logo_bottom_y = 30
    if logo_url:
        logo_img = await _fetch_image(logo_url)
        if logo_img:
            logo_img.thumbnail(cfg.LOGO_MAX_SIZE, Image.LANCZOS)
            _paste_centre_x(bg, logo_img, logo_bottom_y)
            logo_bottom_y += logo_img.height + 20

    # ── VS row (centred vertically in remaining space above time bar) ──────────
    centre_y = (logo_bottom_y + H - 80) // 2 - cfg.TEAM_FONT_SIZE // 2

    # Measure each text piece
    t1_w, t1_h = _text_size(draw, team1, font_team)
    vs_w, vs_h = _text_size(draw, " VS ", font_vs)
    t2_w, t2_h = _text_size(draw, team2, font_team)

    gap = 30
    total_w = t1_w + gap + vs_w + gap + t2_w
    start_x = (W - total_w) // 2

    # Team 1
    draw.text(
        (start_x, centre_y + (vs_h - t1_h) // 2),
        team1,
        font=font_team,
        fill=(255, 255, 255, 255),
    )

    # VS  (gold)
    draw.text(
        (start_x + t1_w + gap, centre_y),
        "VS",
        font=font_vs,
        fill=(255, 215, 0, 255),
    )

    # Team 2
    draw.text(
        (start_x + t1_w + gap + vs_w + gap, centre_y + (vs_h - t2_h) // 2),
        team2,
        font=font_team,
        fill=(255, 255, 255, 255),
    )

    # ── Time bar (bottom-centre) ───────────────────────────────────────────────
    tw, th = _text_size(draw, time_str, font_time)
    draw.text(
        ((W - tw) // 2, H - th - 24),
        time_str,
        font=font_time,
        fill=(200, 200, 200, 255),
    )

    # ── Thumbnail (bottom-right) ───────────────────────────────────────────────
    if thumbnail_url:
        thumb = await _fetch_image(thumbnail_url)
        if thumb:
            thumb.thumbnail(cfg.THUMBNAIL_SIZE, Image.LANCZOS)
            _paste_bottom_right(bg, thumb)

    # ── Output ─────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ── Utility: get latest image URL from a Discord channel ─────────────────────

async def get_latest_channel_image(bot, channel_id: int) -> str | None:
    """
    Scan recent messages in a channel and return the URL of the first image found.
    Used to pull the thumbnail from the configured thumbnail_channel.
    """
    ch = bot.get_channel(int(channel_id))
    if ch is None:
        return None
    try:
        async for msg in ch.history(limit=20):
            for att in msg.attachments:
                if att.content_type and att.content_type.startswith("image/"):
                    return att.url
            for emb in msg.embeds:
                if emb.image and emb.image.url:
                    return emb.image.url
    except Exception:
        pass
    return None
