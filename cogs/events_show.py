"""
cogs/events_show.py  — /events show
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from utils.events_helpers import build_schedule_embed, event_autocomplete

class EventsShowCog(commands.Cog):
    from cogs.events_group import events_group

    @events_group.command(name="show", description="แสดงรายละเอียดทั้งหมดของ event (เห็นเฉพาะคุณ)")
    @app_commands.describe(title="เลือก event ที่ต้องการดู (autocomplete)")
    @app_commands.autocomplete(title=event_autocomplete)
    async def events_show(self, interaction: discord.Interaction, title: str) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, _ = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        col   = db.events_col(interaction.guild_id, active_tour)
        event = await col.find_one({"title": title})
        if not event:
            return await interaction.followup.send(f"❌ ไม่พบ event `{title}`", ephemeral=True)
        embed = build_schedule_embed(event, interaction.guild)
        embed.set_footer(text=f"สถานะ: {event.get('status','ไม่ทราบ')}  |  DB ID: {event['_id']}")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventsShowCog(bot))
