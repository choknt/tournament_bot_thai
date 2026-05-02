"""
cogs/events.py — /events ทุกคำสั่งรวมในไฟล์เดียว
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from bson import ObjectId
import db
from config import COLOR_SCHEDULE
from utils.events_helpers import (
    StaffView, build_schedule_embed, build_results_embed,
    event_autocomplete, has_op_role, log_transcript,
    to_timestamp, utc_str,
)
from utils.image_gen import generate_match_card, get_latest_channel_image


class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    events = app_commands.Group(name="events", description="จัดการการแข่งขันทัวร์นาเมนท์")

    # ── /events create ────────────────────────────────────────────────────────
    @events.command(name="create", description="สร้างตารางแข่งขันแมตช์ใหม่")
    @app_commands.describe(
        team1="ชื่อกัปตันทีม 1", team2="ชื่อกัปตันทีม 2",
        dd="วันที่แข่ง (1-31)", mm="เดือน (1-12)", yyyy="ปี",
        hour="ชั่วโมง", minute="นาที (0-59)",
        ampm="AM หรือ PM — ไม่กรอกถ้าใช้ 24 ชั่วโมง UTC",
        tour_name="ชื่อทัวร์ (ไม่บังคับ)", group_name="ชื่อกลุ่ม เช่น กลุ่ม A",
        round_no="รอบการแข่งขัน เช่น รอบแรก", channel="ช่อง Discord ของแมตช์",
        captain1="กัปตันทีม 1 (Discord user)", captain2="กัปตันทีม 2 (Discord user)",
        judge="กรรมการ (Discord user)", recorder="ผู้บันทึก (Discord user)",
        image_url="URL รูปภาพ (ไม่บังคับ)", remarks="หมายเหตุ (ไม่บังคับ)",
    )
    async def events_create(
        self, interaction: discord.Interaction,
        team1: str, team2: str, dd: int, mm: int, yyyy: int,
        hour: int, minute: int, ampm: str | None = None,
        tour_name: str | None = None, group_name: str | None = None,
        round_no: str | None = None, channel: discord.TextChannel | None = None,
        captain1: discord.Member | None = None, captain2: discord.Member | None = None,
        judge: discord.Member | None = None, recorder: discord.Member | None = None,
        image_url: str | None = None, remarks: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        if not has_op_role(interaction.user, cfg):
            return await interaction.followup.send("❌ คุณต้องมีบทบาทผู้จัดการบอท", ephemeral=True)
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
            "channel_id":    channel.id    if channel   else None,
            "captain1_id":   captain1.id   if captain1  else None,
            "captain1_name": captain1.name if captain1  else team1,
            "captain2_id":   captain2.id   if captain2  else None,
            "captain2_name": captain2.name if captain2  else team2,
            "judge_id":      judge.id      if judge     else None,
            "judge_name":    judge.name    if judge     else None,
            "recorder_id":   recorder.id   if recorder  else None,
            "recorder_name": recorder.name if recorder  else None,
            "image_url": image_url, "remarks": remarks,
            "status": "กำหนดการแล้ว", "message_id": None, "schedule_channel_id": None,
        }
        col = db.events_col(interaction.guild_id, active_tour)
        ins = await col.insert_one(event_doc)
        oid = str(ins.inserted_id)

        logo_url = cfg.get("tour_logo"); thumb_url = None
        tc = cfg.get("thumbnail_channel")
        if tc: thumb_url = await get_latest_channel_image(self.bot, int(tc))
        card_buf = await generate_match_card(
            team1=captain1.name if captain1 else team1,
            team2=captain2.name if captain2 else team2,
            time_str=utc_str(event_doc), logo_url=logo_url, thumbnail_url=thumb_url)
        card_file = discord.File(fp=card_buf, filename="match_card.png")

        sched_ch_id = cfg.get("schedule_channel")
        sched_ch = interaction.guild.get_channel(int(sched_ch_id)) if sched_ch_id else None
        if not sched_ch:
            return await interaction.followup.send("❌ ยังไม่ได้ตั้ง `ช่องตารางแข่ง` ใน /config set", ephemeral=True)

        view = StaffView(oid, interaction.guild_id)
        self.bot.add_view(view)
        msg = await sched_ch.send(file=card_file, embed=build_schedule_embed(event_doc, interaction.guild), view=view)
        await col.update_one({"_id": ins.inserted_id},
                             {"$set": {"message_id": msg.id, "schedule_channel_id": sched_ch.id}})

        notif_ch_id = cfg.get("notification_channel")
        notif_ch = interaction.guild.get_channel(int(notif_ch_id)) if notif_ch_id else None
        if notif_ch:
            pings = " ".join(m.mention for m in [captain1, captain2] if m)
            if pings:
                await notif_ch.send(f"📢 มีการสร้างตารางแข่ง: **{title}**\n{pings}",
                    embed=discord.Embed(description=f"<t:{ts}> (<t:{ts}:R>)", color=COLOR_SCHEDULE))

        await interaction.followup.send(f"✅ สร้าง event **{title}** โพสต์ใน {sched_ch.mention} แล้ว", ephemeral=True)
        await log_transcript(interaction, cfg, f"📅 สร้าง event **{title}** โดย {interaction.user.mention}")

    # ── /events edit ──────────────────────────────────────────────────────────
    @events.command(name="edit", description="แก้ไขข้อมูล event ที่มีอยู่")
    @app_commands.describe(
        title="เลือก event ที่ต้องการแก้ไข",
        team1="ชื่อกัปตันทีม 1 ใหม่", team2="ชื่อกัปตันทีม 2 ใหม่",
        dd="วันที่ใหม่", mm="เดือนใหม่", yyyy="ปีใหม่",
        hour="ชั่วโมงใหม่", minute="นาทีใหม่", ampm="AM/PM",
        tour_name="ชื่อทัวร์ใหม่", group_name="ชื่อกลุ่มใหม่", round_no="รอบใหม่",
        channel="ช่องแมตช์ใหม่", captain1="กัปตันทีม 1 ใหม่", captain2="กัปตันทีม 2 ใหม่",
        judge="กรรมการใหม่", recorder="ผู้บันทึกใหม่",
        image_url="URL รูปภาพใหม่", remarks="หมายเหตุใหม่",
    )
    @app_commands.autocomplete(title=event_autocomplete)
    async def events_edit(
        self, interaction: discord.Interaction, title: str,
        team1: str | None = None, team2: str | None = None,
        dd: int | None = None, mm: int | None = None, yyyy: int | None = None,
        hour: int | None = None, minute: int | None = None, ampm: str | None = None,
        tour_name: str | None = None, group_name: str | None = None, round_no: str | None = None,
        channel: discord.TextChannel | None = None,
        captain1: discord.Member | None = None, captain2: discord.Member | None = None,
        judge: discord.Member | None = None, recorder: discord.Member | None = None,
        image_url: str | None = None, remarks: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        if not has_op_role(interaction.user, cfg):
            return await interaction.followup.send("❌ คุณต้องมีบทบาทผู้จัดการบอท", ephemeral=True)
        col = db.events_col(interaction.guild_id, active_tour)
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
        if captain1:           updates["captain1_id"] = captain1.id; updates["captain1_name"] = captain1.name
        if captain2:           updates["captain2_id"] = captain2.id; updates["captain2_name"] = captain2.name
        if judge:              updates["judge_id"] = judge.id;       updates["judge_name"] = judge.name
        if recorder:           updates["recorder_id"] = recorder.id; updates["recorder_name"] = recorder.name
        if image_url is not None: updates["image_url"] = image_url
        if remarks is not None:   updates["remarks"]   = remarks

        if not updates:
            return await interaction.followup.send("⚠️ ไม่มีการเปลี่ยนแปลง", ephemeral=True)

        if {"dd", "mm", "yyyy", "hour", "minute", "ampm"} & set(updates):
            merged = {**event, **updates}
            try: updates["timestamp"] = to_timestamp(merged["dd"], merged["mm"], merged["yyyy"],
                                                     merged["hour"], merged["minute"], merged.get("ampm"))
            except: pass

        new_t1 = updates.get("team1", event["team1"])
        new_t2 = updates.get("team2", event["team2"])
        new_rn = updates.get("round_no", event.get("round_no"))
        new_title = f"{new_t1} vs {new_t2}" + (f"  [{new_rn}]" if new_rn else "")
        updates["title"] = new_title

        await col.update_one({"_id": event["_id"]}, {"$set": updates})
        updated = await col.find_one({"_id": event["_id"]})

        msg_id = event.get("message_id"); sched_ch_id = event.get("schedule_channel_id")
        if msg_id and sched_ch_id:
            sched_ch = interaction.guild.get_channel(int(sched_ch_id))
            if sched_ch:
                try:
                    msg = await sched_ch.fetch_message(int(msg_id))
                    view = StaffView(str(event["_id"]), interaction.guild_id)
                    self.bot.add_view(view)
                    await msg.edit(embed=build_schedule_embed(updated, interaction.guild), view=view)
                except Exception: pass

        await interaction.followup.send(f"✅ แก้ไข event **{new_title}** เรียบร้อยแล้ว", ephemeral=True)
        await log_transcript(interaction, cfg, f"✏️ แก้ไข event **{new_title}** โดย {interaction.user.mention}")

    # ── /events delete ────────────────────────────────────────────────────────
    @events.command(name="delete", description="ลบ event การแข่งขัน")
    @app_commands.describe(title="เลือก event ที่ต้องการลบ",
                           reason="สาเหตุที่ลบ (ไม่บังคับ)")
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
        col = db.events_col(interaction.guild_id, active_tour)
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

    # ── /events show ──────────────────────────────────────────────────────────
    @events.command(name="show", description="แสดงรายละเอียดทั้งหมดของ event")
    @app_commands.describe(title="เลือก event ที่ต้องการดู")
    @app_commands.autocomplete(title=event_autocomplete)
    async def events_show(self, interaction: discord.Interaction, title: str) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, _ = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        col = db.events_col(interaction.guild_id, active_tour)
        event = await col.find_one({"title": title})
        if not event:
            return await interaction.followup.send(f"❌ ไม่พบ event `{title}`", ephemeral=True)
        embed = build_schedule_embed(event, interaction.guild)
        embed.set_footer(text=f"สถานะ: {event.get('status','ไม่ทราบ')}  |  ID: {event['_id']}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ── /events results ───────────────────────────────────────────────────────
    @events.command(name="results", description="โพสต์ผลการแข่งขันไปที่ช่องผลการแข่ง")
    @app_commands.describe(
        event="เลือก event (autocomplete)",
        team1_score="คะแนนทีม 1", team2_score="คะแนนทีม 2",
        number_of_matches="จำนวนแมตช์ทั้งหมด (ไม่บังคับ)",
        remarks="หมายเหตุ (ไม่บังคับ)", rec_link="ลิงก์บันทึกการแข่ง (ไม่บังคับ)",
        screenshot1="ภาพหน้าจอที่ 1 (แสดงใน embed)",
        screenshot2="ภาพหน้าจอที่ 2", screenshot3="ภาพหน้าจอที่ 3",
        screenshot4="ภาพหน้าจอที่ 4", screenshot5="ภาพหน้าจอที่ 5",
        screenshot6="ภาพหน้าจอที่ 6", screenshot7="ภาพหน้าจอที่ 7",
        screenshot8="ภาพหน้าจอที่ 8", screenshot9="ภาพหน้าจอที่ 9",
    )
    @app_commands.autocomplete(event=event_autocomplete)
    async def events_results(
        self, interaction: discord.Interaction,
        event: str, team1_score: str, team2_score: str,
        number_of_matches: int | None = None, remarks: str | None = None,
        rec_link: str | None = None,
        screenshot1: discord.Attachment | None = None,
        screenshot2: discord.Attachment | None = None,
        screenshot3: discord.Attachment | None = None,
        screenshot4: discord.Attachment | None = None,
        screenshot5: discord.Attachment | None = None,
        screenshot6: discord.Attachment | None = None,
        screenshot7: discord.Attachment | None = None,
        screenshot8: discord.Attachment | None = None,
        screenshot9: discord.Attachment | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        if not has_op_role(interaction.user, cfg):
            return await interaction.followup.send("❌ คุณต้องมีบทบาทผู้จัดการบอท", ephemeral=True)
        col = db.events_col(interaction.guild_id, active_tour)
        event_doc = await col.find_one({"title": event})
        if not event_doc:
            return await interaction.followup.send(f"❌ ไม่พบ event `{event}`", ephemeral=True)

        shots = [att.url for att in [screenshot1, screenshot2, screenshot3,
                                      screenshot4, screenshot5, screenshot6,
                                      screenshot7, screenshot8, screenshot9] if att]
        result_doc = {"event_title": event, "team1_score": team1_score, "team2_score": team2_score,
                      "number_of_matches": number_of_matches, "remarks": remarks,
                      "rec_link": rec_link, "screenshots": shots}

        res_ch_id = cfg.get("results_channel")
        res_ch = interaction.guild.get_channel(int(res_ch_id)) if res_ch_id else None
        if not res_ch:
            return await interaction.followup.send("❌ ยังไม่ได้ตั้ง `ช่องผลการแข่ง` ใน /config set", ephemeral=True)

        if len(shots) > 1:
            for i in range(0, len(shots[1:]), 5):
                await res_ch.send(content="\n".join(shots[1:][i:i+5]))

        logo_url = cfg.get("tour_logo"); thumb_url = None
        tc = cfg.get("thumbnail_channel")
        if tc: thumb_url = await get_latest_channel_image(self.bot, int(tc))
        t1 = event_doc.get("captain1_name") or event_doc.get("team1", "ทีม 1")
        t2 = event_doc.get("captain2_name") or event_doc.get("team2", "ทีม 2")
        card_buf = await generate_match_card(team1=t1, team2=t2, time_str=utc_str(event_doc),
                                             logo_url=logo_url, thumbnail_url=thumb_url)
        card_file = discord.File(fp=card_buf, filename="results_card.png")
        embed = build_results_embed(event_doc, result_doc, interaction.guild)
        await res_ch.send(file=card_file, embed=embed)

        await col.update_one({"_id": event_doc["_id"]}, {"$set": {"status": "จบแล้ว"}})
        result_doc["event_id"] = event_doc["_id"]
        await db.results_col(interaction.guild_id, active_tour).insert_one(result_doc)

        await interaction.followup.send(f"✅ โพสต์ผลการแข่ง **{event}** ใน {res_ch.mention} แล้ว", ephemeral=True)
        await log_transcript(interaction, cfg,
            f"🏁 โพสต์ผล **{event}** โดย {interaction.user.mention} | {team1_score}–{team2_score}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventsCog(bot))
