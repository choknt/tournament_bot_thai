"""
main.py — จุดเริ่มต้นของ Tournament Bot
รันด้วย:  python main.py
"""
from __future__ import annotations
import asyncio
import logging
import discord
from discord.ext import commands
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("tournament_bot")

# ── โหลด cog ทีละไฟล์ — คอมเมนต์บรรทัดไหนเพื่อปิดคำสั่งนั้น ──────────────
EXTENSIONS = [
    "cogs.send_regis",      # /send_regis    — ประกาศรับสมัคร
    "cogs.staff_data",      # /staff_data    — บันทึกข้อมูลสตาฟ
    "cogs.config_cmd",      # /config        — ตั้งค่าทัวร์
    "cogs.events_create",   # /events create — สร้างตารางแข่ง
    "cogs.events_edit",     # /events edit   — แก้ไข event
    "cogs.events_delete",   # /events delete — ลบ event
    "cogs.events_show",     # /events show   — ดูข้อมูล event
    "cogs.events_results",  # /events results — โพสต์ผลแข่ง
]

class TournamentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info(f"โหลดแล้ว: {ext}")
            except Exception as exc:
                log.error(f"โหลดไม่ได้ {ext}: {exc}", exc_info=True)
        from cogs.events_group import events_group
        self.tree.add_command(events_group)
        await self.tree.sync()
        log.info("ซิงก์ slash commands เรียบร้อย")

    async def on_ready(self):
        log.info(f"เข้าสู่ระบบในชื่อ  {self.user}  (ID: {self.user.id})")
        log.info("─" * 40)
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, name="ทัวร์นาเมนท์ 🏆"))

async def main():
    bot = TournamentBot()
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
