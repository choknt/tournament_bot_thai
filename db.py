"""
db.py — MongoDB helper layer.

Database naming:
  Each tournament gets its own Mongo database:
    name = "{guild_id}_{slug(tour_name)}"
  e.g.  1234567890_mw_season_1

A separate meta database (tournament_bot_meta) tracks
which tournament is currently active per guild, and which
tournaments have ever been created.
"""

from __future__ import annotations

import re
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

_client: AsyncIOMotorClient | None = None


# ── Internal ──────────────────────────────────────────────────────────────────

def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        from config import MONGO_URI
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


def _slug(name: str) -> str:
    """Convert tournament name to a safe MongoDB database name segment."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_") or "unnamed"


# ── Tournament database & collections ────────────────────────────────────────

def tournament_db(guild_id: int, tour_name: str) -> AsyncIOMotorDatabase:
    """Return the database for a specific guild+tournament pair."""
    db_name = f"{guild_id}_{_slug(tour_name)}"
    return _get_client()[db_name]


def config_col(guild_id: int, tour_name: str) -> AsyncIOMotorCollection:
    return tournament_db(guild_id, tour_name)["config"]

def events_col(guild_id: int, tour_name: str) -> AsyncIOMotorCollection:
    return tournament_db(guild_id, tour_name)["events"]

def players_col(guild_id: int, tour_name: str) -> AsyncIOMotorCollection:
    return tournament_db(guild_id, tour_name)["players"]

def staff_col(guild_id: int, tour_name: str) -> AsyncIOMotorCollection:
    return tournament_db(guild_id, tour_name)["staff"]

def results_col(guild_id: int, tour_name: str) -> AsyncIOMotorCollection:
    return tournament_db(guild_id, tour_name)["results"]


# ── Meta database (active tournament tracking) ────────────────────────────────

def _meta_guilds() -> AsyncIOMotorCollection:
    return _get_client()["tournament_bot_meta"]["guilds"]


async def get_active_tour(guild_id: int) -> str | None:
    """Return the active tournament name for a guild, or None."""
    doc = await _meta_guilds().find_one({"guild_id": guild_id})
    return doc.get("active_tour") if doc else None


async def set_active_tour(guild_id: int, tour_name: str) -> None:
    await _meta_guilds().update_one(
        {"guild_id": guild_id},
        {"$set": {"active_tour": tour_name, "guild_id": guild_id}},
        upsert=True,
    )


async def add_tour(guild_id: int, tour_name: str) -> None:
    """Register a new tournament name for a guild (for listing purposes)."""
    await _meta_guilds().update_one(
        {"guild_id": guild_id},
        {
            "$addToSet": {"tours": tour_name},
            "$set": {"guild_id": guild_id},
        },
        upsert=True,
    )


async def list_tours(guild_id: int) -> list[str]:
    doc = await _meta_guilds().find_one({"guild_id": guild_id})
    return doc.get("tours", []) if doc else []


# ── Convenience: get current config for a guild ───────────────────────────────

async def get_active_config(guild_id: int) -> dict | None:
    """Return the config document for the guild's active tournament."""
    tour = await get_active_tour(guild_id)
    if not tour:
        return None
    return await config_col(guild_id, tour).find_one({}, {"_id": 0})


async def require_active(guild_id: int):
    """
    Return (tour_name, config_doc).
    Raises ValueError if no active tournament is set.
    """
    tour = await get_active_tour(guild_id)
    if not tour:
        raise ValueError("ยังไม่มีทัวร์ที่ใช้งานอยู่ กรุณาให้แอดมินรัน `/config set` ก่อน")
    cfg = await config_col(guild_id, tour).find_one({}, {"_id": 0})
    if not cfg:
        raise ValueError("ไม่พบข้อมูลตั้งค่าของทัวร์นี้ กรุณารัน `/config set` ใหม่อีกครั้ง")
    return tour, cfg
