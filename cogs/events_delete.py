"""
cogs/events_delete.py  — /events delete
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from utils.events_helpers import event_autocomplete, has_op_role, log_transcript

class EventsDeleteCog(commands.Cog):
    from cogs.events_group import events_group

    @events_group.command(name="delete", description="ลบ event การแข่งขัน")
    @app_commands.describe(title="เลือก event ที่ต้องการลบ (autocomplete)",
                           reason="สาเหตุที่ลบ (ไม่บังคับ จะถูกบันทึกใน transcript)")
    @app_commands.autocomplete(title=event_autocomplete)
    async def events_delete(self, interaction: discord.Interaction,
                            title: str, reason: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        if not has_op_role(interaction.user, cfg):
            return await interaction.followup.send("❌ คุณต้องมีบทบาทผู้จัดการบอท", ephemeral=True)
        col   = db.events_col(interaction.guild_id, active_tour)
        event = await col.find_one({"title": title})
        if not event:
            return await interaction.followup.send(f"❌ ไม่พบ event `{title}`", ephemeral=True)
        msg_id = event.get("message_id"); sched_ch_id = event.get("schedule_channel_id")
        if msg_id and sched_ch_id:
            sched_ch = interaction.guild.get_channel(int(sched_ch_id))
            if sched_ch:
                try:
                    msg = await sched_ch.fetch_message(int(msg_id))
                    await msg.delete()
                except Exception: pass
        await col.delete_one({"_id": event["_id"]})
        await interaction.followup.send(f"🗑️ ลบ event **{title}** เรียบร้อยแล้ว", ephemeral=True)
        log_msg = f"🗑️ ลบ event **{title}** โดย {interaction.user.mention}"
        if reason: log_msg += f"\n> สาเหตุ: {reason}"
        await log_transcript(interaction, cfg, log_msg)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventsDeleteCog(bot))
