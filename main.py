"""
main.py — Tournament Bot entry point.
"""
from __future__ import annotations
import asyncio
import logging
import discord
from discord.ext import commands
from config import BOT_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("tournament_bot")

EXTENSIONS = [
    "cogs.send_regis",
    "cogs.staff_data",
    "cogs.config_cmd",
    "cogs.events",
]


class TournamentBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info(f"โหลดแล้ว: {ext}")
            except Exception as exc:
                log.error(f"โหลดไม่ได้ {ext}: {exc}", exc_info=True)
        await self.tree.sync()
        log.info("Slash commands synced.")

    async def on_ready(self) -> None:
        log.info(f"ออนไลน์: {self.user}  (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="ทัวร์นาเมนท์ 🏆",
            )
        )


async def main() -> None:
    bot = TournamentBot()
    async with bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
