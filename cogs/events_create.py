"""
cogs/events_create.py  — /events create
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from config import COLOR_SCHEDULE
from utils.events_helpers import StaffView, build_schedule_embed, event_autocomplete, has_op_role, log_transcript, to_timestamp, utc_str
from utils.image_gen import generate_match_card, get_latest_channel_image

class EventsCreateCog(commands.Cog):
    from cogs.events_group import events_group
    def __init__(self, bot): self.bot = bot

    @events_group.command(name="create", description="สร้างตารางแข่งขันแมตช์ใหม่")
    @app_commands.describe(
        team1="ชื่อกัปตันทีม 1", team2="ชื่อกัปตันทีม 2",
        dd="วันที่แข่ง (1-31)", mm="เดือน (1-12)", yyyy="ปี",
        hour="ชั่วโมง (24h หรือ 12h)", minute="นาที (0-59)",
        ampm="AM หรือ PM — ไม่ต้องกรอกถ้าใช้ 24 ชั่วโมง UTC",
        tour_name="ชื่อทัวร์ (ไม่บังคับ ใช้ทัวร์ปัจจุบันถ้าไม่กรอก)",
        group_name="ชื่อกลุ่ม เช่น กลุ่ม A",
        round_no="รอบการแข่งขัน เช่น รอบแรก, รอบรองชนะเลิศ",
        channel="ช่อง Discord ของแมตช์นี้",
        captain1="กัปตันทีม 1 (เลือก Discord user)",
        captain2="กัปตันทีม 2 (เลือก Discord user)",
        judge="กรรมการ (เลือก Discord user)",
        recorder="ผู้บันทึก (เลือก Discord user)",
        image_url="URL รูปภาพเพิ่มเติม (ไม่บังคับ)",
        remarks="หมายเหตุเพิ่มเติม (ไม่บังคับ)",
    )
    async def events_create(self, interaction: discord.Interaction,
                            team1: str, team2: str, dd: int, mm: int, yyyy: int,
                            hour: int, minute: int, ampm: str | None = None,
                            tour_name: str | None = None, group_name: str | None = None,
                            round_no: str | None = None, channel: discord.TextChannel | None = None,
                            captain1: discord.Member | None = None, captain2: discord.Member | None = None,
                            judge: discord.Member | None = None, recorder: discord.Member | None = None,
                            image_url: str | None = None, remarks: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        if not has_op_role(interaction.user, cfg):
            return await interaction.followup.send("❌ คุณต้องมีบทบาทผู้จัดการบอทเพื่อใช้คำสั่งนี้", ephemeral=True)
        used_tour = tour_name or cfg.get("tour_name") or active_tour
        try:
            ts = to_timestamp(dd, mm, yyyy, hour, minute, ampm)
        except (ValueError, OverflowError) as exc:
            return await interaction.followup.send(f"❌ วันที่/เวลาไม่ถูกต้อง: {exc}", ephemeral=True)
        title = f"{team1} vs {team2}" + (f"  [{round_no}]" if round_no else "")
        event_doc = {
            "title": title, "team1": team1, "team2": team2,
            "dd": dd, "mm": mm, "yyyy": yyyy, "hour": hour, "minute": minute, "ampm": ampm,
            "timestamp": ts, "tour_name": used_tour, "group_name": group_name, "round_no": round_no,
            "channel_id":    channel.id   if channel   else None,
            "captain1_id":   captain1.id  if captain1  else None,
            "captain1_name": captain1.name if captain1 else team1,
            "captain2_id":   captain2.id  if captain2  else None,
            "captain2_name": captain2.name if captain2 else team2,
            "judge_id":      judge.id     if judge     else None,
            "judge_name":    judge.name   if judge     else None,
            "recorder_id":   recorder.id  if recorder  else None,
            "recorder_name": recorder.name if recorder  else None,
            "image_url": image_url, "remarks": remarks,
            "status": "กำหนดการแล้ว", "message_id": None, "schedule_channel_id": None,
        }
        col = db.events_col(interaction.guild_id, active_tour)
        ins = await col.insert_one(event_doc)
        oid = str(ins.inserted_id)
        logo_url  = cfg.get("tour_logo")
        thumb_url = None
        tc = cfg.get("thumbnail_channel")
        if tc: thumb_url = await get_latest_channel_image(self.bot, int(tc))
        card_buf  = await generate_match_card(
            team1=captain1.name if captain1 else team1,
            team2=captain2.name if captain2 else team2,
            time_str=utc_str(event_doc), logo_url=logo_url, thumbnail_url=thumb_url)
        card_file = discord.File(fp=card_buf, filename="match_card.png")
        sched_ch_id = cfg.get("schedule_channel")
        sched_ch    = interaction.guild.get_channel(int(sched_ch_id)) if sched_ch_id else None
        if not sched_ch:
            return await interaction.followup.send("❌ ยังไม่ได้ตั้ง `ช่องตารางแข่ง` ใน /config set", ephemeral=True)
        view = StaffView(oid, interaction.guild_id)
        self.bot.add_view(view)
        msg  = await sched_ch.send(file=card_file, embed=build_schedule_embed(event_doc, interaction.guild), view=view)
        await col.update_one({"_id": ins.inserted_id},
                             {"$set": {"message_id": msg.id, "schedule_channel_id": sched_ch.id}})
        notif_ch_id = cfg.get("notification_channel")
        notif_ch    = interaction.guild.get_channel(int(notif_ch_id)) if notif_ch_id else None
        if notif_ch:
            pings = " ".join(m.mention for m in [captain1, captain2] if m)
            if pings:
                await notif_ch.send(f"📢 มีการสร้างตารางแข่ง: **{title}**\n{pings}",
                    embed=discord.Embed(description=f"<t:{ts}> (<t:{ts}:R>)", color=COLOR_SCHEDULE))
        await interaction.followup.send(f"✅ สร้าง event **{title}** และโพสต์ใน {sched_ch.mention} แล้ว", ephemeral=True)
        await log_transcript(interaction, cfg, f"📅 สร้าง event **{title}** โดย {interaction.user.mention}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventsCreateCog(bot))
