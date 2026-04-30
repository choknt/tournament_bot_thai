"""
cogs/staff_data.py  — /staff_data
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from config import COLOR_INFO, STAFF_DATA_CHANNEL_ID

class StaffDataCog(commands.Cog):
    @app_commands.command(name="staff_data", description="บันทึกข้อมูลสตาฟ (ชื่อในเกม, ID, ข้อมูล Discord)")
    @app_commands.describe(
        game_name="ชื่อในเกมของคุณ",
        game_id="ID ในเกมของคุณ",
        discord_username="ชื่อผู้ใช้ Discord",
        discord_tag="แท็ก Discord เช่น chok_nt#0000",
        discord_id="ID Discord (เลข 18 หลัก)",
    )
    async def staff_data(self, interaction: discord.Interaction,
                         game_name: str, game_id: str,
                         discord_username: str, discord_tag: str, discord_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title="🛡️  ข้อมูลสตาฟ", color=COLOR_INFO)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="ชื่อในเกม",       value=game_name,        inline=True)
        embed.add_field(name="ID ในเกม",         value=game_id,          inline=True)
        embed.add_field(name="ชื่อผู้ใช้ Discord", value=discord_username, inline=True)
        embed.add_field(name="แท็ก Discord",     value=discord_tag,      inline=True)
        embed.add_field(name="ID Discord",       value=discord_id,       inline=True)
        log_ch = interaction.client.get_channel(STAFF_DATA_CHANNEL_ID)
        if log_ch:
            await log_ch.send(embed=embed)
        try:
            tour, _ = await db.require_active(interaction.guild_id)
            await db.staff_col(interaction.guild_id, tour).update_one(
                {"discord_id": discord_id},
                {"$set": {"game_name": game_name, "game_id": game_id,
                          "discord_username": discord_username, "discord_tag": discord_tag,
                          "discord_id": discord_id}},
                upsert=True,
            )
        except Exception:
            pass
        await interaction.followup.send("✅ บันทึกข้อมูลสตาฟเรียบร้อยแล้ว", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StaffDataCog(bot))
