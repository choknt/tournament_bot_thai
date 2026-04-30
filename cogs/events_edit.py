"""
cogs/events_edit.py  — /events edit
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from utils.events_helpers import StaffView, build_schedule_embed, event_autocomplete, has_op_role, log_transcript, to_timestamp

class EventsEditCog(commands.Cog):
    from cogs.events_group import events_group
    def __init__(self, bot): self.bot = bot

    @events_group.command(name="edit", description="แก้ไขข้อมูล event ที่มีอยู่")
    @app_commands.describe(
        title="เลือก event ที่ต้องการแก้ไข (autocomplete)",
        team1="ชื่อกัปตันทีม 1 ใหม่", team2="ชื่อกัปตันทีม 2 ใหม่",
        dd="วันที่ใหม่", mm="เดือนใหม่", yyyy="ปีใหม่",
        hour="ชั่วโมงใหม่", minute="นาทีใหม่", ampm="AM/PM",
        tour_name="ชื่อทัวร์ใหม่", group_name="ชื่อกลุ่มใหม่",
        round_no="รอบใหม่", channel="ช่องแมตช์ใหม่",
        captain1="กัปตันทีม 1 ใหม่", captain2="กัปตันทีม 2 ใหม่",
        judge="กรรมการใหม่", recorder="ผู้บันทึกใหม่",
        image_url="URL รูปภาพใหม่", remarks="หมายเหตุใหม่",
    )
    @app_commands.autocomplete(title=event_autocomplete)
    async def events_edit(self, interaction: discord.Interaction, title: str,
                          team1: str | None=None, team2: str | None=None,
                          dd: int | None=None, mm: int | None=None, yyyy: int | None=None,
                          hour: int | None=None, minute: int | None=None, ampm: str | None=None,
                          tour_name: str | None=None, group_name: str | None=None, round_no: str | None=None,
                          channel: discord.TextChannel | None=None,
                          captain1: discord.Member | None=None, captain2: discord.Member | None=None,
                          judge: discord.Member | None=None, recorder: discord.Member | None=None,
                          image_url: str | None=None, remarks: str | None=None) -> None:
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
        updates: dict = {}
        if team1:              updates["team1"]         = team1
        if team2:              updates["team2"]         = team2
        if dd:                 updates["dd"]            = dd
        if mm:                 updates["mm"]            = mm
        if yyyy:               updates["yyyy"]          = yyyy
        if hour is not None:   updates["hour"]          = hour
        if minute is not None: updates["minute"]        = minute
        if ampm is not None:   updates["ampm"]          = ampm
        if tour_name:          updates["tour_name"]     = tour_name
        if group_name:         updates["group_name"]    = group_name
        if round_no:           updates["round_no"]      = round_no
        if channel:            updates["channel_id"]    = channel.id
        if captain1:           updates["captain1_id"]   = captain1.id;  updates["captain1_name"] = captain1.name
        if captain2:           updates["captain2_id"]   = captain2.id;  updates["captain2_name"] = captain2.name
        if judge:              updates["judge_id"]      = judge.id;     updates["judge_name"]    = judge.name
        if recorder:           updates["recorder_id"]   = recorder.id;  updates["recorder_name"] = recorder.name
        if image_url is not None: updates["image_url"]  = image_url
        if remarks is not None:   updates["remarks"]    = remarks
        if not updates:
            return await interaction.followup.send("⚠️ ไม่มีการเปลี่ยนแปลง", ephemeral=True)
        if {"dd","mm","yyyy","hour","minute","ampm"} & set(updates):
            merged = {**event, **updates}
            try: updates["timestamp"] = to_timestamp(merged["dd"],merged["mm"],merged["yyyy"],merged["hour"],merged["minute"],merged.get("ampm"))
            except: pass
        new_t1 = updates.get("team1",event["team1"]); new_t2 = updates.get("team2",event["team2"])
        new_rn = updates.get("round_no",event.get("round_no"))
        new_title = f"{new_t1} vs {new_t2}" + (f"  [{new_rn}]" if new_rn else "")
        updates["title"] = new_title
        await col.update_one({"_id": event["_id"]}, {"$set": updates})
        updated = await col.find_one({"_id": event["_id"]})
        msg_id = event.get("message_id"); sched_ch_id = event.get("schedule_channel_id")
        if msg_id and sched_ch_id:
            sched_ch = interaction.guild.get_channel(int(sched_ch_id))
            if sched_ch:
                try:
                    msg  = await sched_ch.fetch_message(int(msg_id))
                    view = StaffView(str(event["_id"]), interaction.guild_id)
                    self.bot.add_view(view)
                    await msg.edit(embed=build_schedule_embed(updated, interaction.guild), view=view)
                except Exception: pass
        await interaction.followup.send(f"✅ แก้ไข event **{new_title}** เรียบร้อยแล้ว", ephemeral=True)
        await log_transcript(interaction, cfg, f"✏️ แก้ไข event **{new_title}** โดย {interaction.user.mention}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventsEditCog(bot))
