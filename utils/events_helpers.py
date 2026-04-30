"""
utils/events_helpers.py — ฟังก์ชันกลางที่ทุก /events ใช้ร่วมกัน
"""
from __future__ import annotations
from datetime import datetime, timezone
import discord
from bson import ObjectId
from discord import app_commands
import db
from config import COLOR_SCHEDULE, COLOR_RESULTS

# ── เวลา ──────────────────────────────────────────────────────────────────────
def to_timestamp(dd, mm, yyyy, hour, minute, ampm=None) -> int:
    h = hour
    if ampm:
        ampm = ampm.upper().strip()
        if ampm == "PM" and h != 12: h += 12
        elif ampm == "AM" and h == 12: h = 0
    return int(datetime(yyyy, mm, dd, h, minute, tzinfo=timezone.utc).timestamp())

def utc_str(event: dict) -> str:
    dd = str(event.get("dd","?")).zfill(2); mm = str(event.get("mm","?")).zfill(2)
    yyyy = event.get("yyyy","????"); hh = str(event.get("hour","?")).zfill(2)
    mn = str(event.get("minute","00")).zfill(2); ap = event.get("ampm","UTC") or "UTC"
    return f"{dd}/{mm}/{yyyy}  {hh}:{mn} {ap}"

def has_op_role(member: discord.Member, cfg: dict) -> bool:
    if member.guild_permissions.administrator: return True
    rid = cfg.get("bot_op_role")
    if not rid: return False
    return any(r.id == int(rid) for r in member.roles)

# ── Embed ตารางแข่ง ──────────────────────────────────────────────────────────
def build_schedule_embed(event: dict, guild: discord.Guild) -> discord.Embed:
    team1 = event.get("team1","TBD"); team2 = event.get("team2","TBD")
    ts = event.get("timestamp", 0)
    embed = discord.Embed(title=f"🗓️  {team1}  vs  {team2}", color=COLOR_SCHEDULE)
    embed.add_field(name="เวลา UTC",    value=f"`{utc_str(event)}`",    inline=False)
    embed.add_field(name="เวลาท้องถิ่น", value=f"<t:{ts}> (<t:{ts}:R>)", inline=False)
    if event.get("tour_name"):  embed.add_field(name="__**ทัวร์นาเมนท์**__", value=event["tour_name"],     inline=True)
    if event.get("group_name"): embed.add_field(name="__**กลุ่ม**__",         value=event["group_name"],    inline=True)
    if event.get("round_no"):   embed.add_field(name="__**รอบ**__",            value=str(event["round_no"]), inline=True)
    ch_id = event.get("channel_id")
    embed.add_field(name="ช่อง", value=f"<#{ch_id}>" if ch_id else "—", inline=False)
    c1_id = event.get("captain1_id"); c1_nm = event.get("captain1_name") or team1
    c2_id = event.get("captain2_id"); c2_nm = event.get("captain2_name") or team2
    embed.add_field(name="กัปตันทีม 1", value=f"<@{c1_id}> ({c1_nm})" if c1_id else c1_nm, inline=True)
    embed.add_field(name="กัปตันทีม 2", value=f"<@{c2_id}> ({c2_nm})" if c2_id else c2_nm, inline=True)
    j_id = event.get("judge_id");    j_nm = event.get("judge_name","TBD")
    r_id = event.get("recorder_id"); r_nm = event.get("recorder_name","TBD")
    embed.add_field(name="__**สตาฟ**__", value=(
        f"▪️ **กรรมการ**: {f'<@{j_id}> ({j_nm})' if j_id else 'TBD'}\n"
        f"▪️ **ผู้บันทึก**: {f'<@{r_id}> ({r_nm})' if r_id else 'TBD'}"
    ), inline=False)
    if event.get("remarks"):   embed.add_field(name="หมายเหตุ", value=event["remarks"], inline=False)
    if event.get("image_url"): embed.set_image(url=event["image_url"])
    return embed

# ── Embed ผลการแข่งขัน ───────────────────────────────────────────────────────
def build_results_embed(event: dict, result: dict, guild: discord.Guild) -> discord.Embed:
    team1 = event.get("team1","TBD"); team2 = event.get("team2","TBD")
    ts = event.get("timestamp",0); s1 = result.get("team1_score","?"); s2 = result.get("team2_score","?")
    try:
        if   int(s1) > int(s2): e1,e2 = "🏆","💀"
        elif int(s2) > int(s1): e1,e2 = "💀","🏆"
        else: e1 = e2 = "🤝"
    except: e1 = e2 = ""
    c1_id = event.get("captain1_id"); c1_nm = event.get("captain1_name") or team1
    c2_id = event.get("captain2_id"); c2_nm = event.get("captain2_name") or team2
    embed = discord.Embed(title=f"⚔️  {team1}  vs  {team2}", color=COLOR_RESULTS)
    embed.add_field(name="เวลาท้องถิ่น", value=f"<t:{ts}> (<t:{ts}:R>)", inline=False)
    if event.get("tour_name"):  embed.add_field(name="__**ทัวร์นาเมนท์**__", value=event["tour_name"],     inline=True)
    if event.get("group_name"): embed.add_field(name="__**กลุ่ม**__",         value=event["group_name"],    inline=True)
    if event.get("round_no"):   embed.add_field(name="__**รอบ**__",            value=str(event["round_no"]), inline=True)
    ch_id = event.get("channel_id")
    embed.add_field(name="ช่อง", value=f"<#{ch_id}>" if ch_id else "—", inline=False)
    embed.add_field(name="กัปตันทีม 1", value=f"<@{c1_id}> ({c1_nm})" if c1_id else c1_nm, inline=True)
    embed.add_field(name="กัปตันทีม 2", value=f"<@{c2_id}> ({c2_nm})" if c2_id else c2_nm, inline=True)
    j_id = event.get("judge_id");    j_nm = event.get("judge_name","N/A")
    r_id = event.get("recorder_id"); r_nm = event.get("recorder_name","N/A")
    embed.add_field(name="__**สตาฟ**__", value=(
        f"▪️ **กรรมการ**: {f'<@{j_id}> ({j_nm})' if j_id else j_nm}\n"
        f"▪️ **ผู้บันทึก**: {f'<@{r_id}> ({r_nm})' if r_id else r_nm}"
    ), inline=False)
    embed.add_field(name="__**ผลการแข่งขัน**__",
        value=f"{e1} {c1_nm} `({s1})` : `({s2})` {c2_nm} {e2}", inline=False)
    num = result.get("number_of_matches")
    if num: embed.add_field(name="จำนวนแมตช์", value=str(num), inline=True)
    if result.get("rec_link"):  embed.add_field(name="🎬 ลิงก์บันทึกการแข่ง", value=result["rec_link"], inline=False)
    if result.get("remarks"):   embed.add_field(name="หมายเหตุ", value=result["remarks"], inline=False)
    shots = result.get("screenshots",[])
    if shots: embed.set_image(url=shots[0])
    return embed

# ── ปุ่มสตาฟ (Persistent) ───────────────────────────────────────────────────
async def handle_staff_click(interaction: discord.Interaction, event_oid: str, staff_type: str) -> None:
    await interaction.response.defer(ephemeral=True)
    try:
        tour, cfg = await db.require_active(interaction.guild_id)
    except ValueError as exc:
        return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
    role_id = cfg.get(f"{staff_type}_role")
    if role_id:
        required = interaction.guild.get_role(int(role_id))
        role_th = "กรรมการ" if staff_type == "judge" else "ผู้บันทึก"
        if required and required not in interaction.user.roles:
            return await interaction.followup.send(
                f"❌ คุณต้องมีบทบาท **{required.name}** เพื่อรับหน้าที่{role_th}", ephemeral=True)
    col = db.events_col(interaction.guild_id, tour)
    event = await col.find_one({"_id": ObjectId(event_oid)})
    if not event:
        return await interaction.followup.send("❌ ไม่พบ Event นี้ในฐานข้อมูล", ephemeral=True)
    current_id = event.get(f"{staff_type}_id")
    if current_id and current_id != interaction.user.id:
        role_th = "กรรมการ" if staff_type == "judge" else "ผู้บันทึก"
        return await interaction.followup.send(f"❌ มีคนรับหน้าที่{role_th}ไปแล้ว", ephemeral=True)
    updates = {f"{staff_type}_id": interaction.user.id, f"{staff_type}_name": interaction.user.name}
    await col.update_one({"_id": ObjectId(event_oid)}, {"$set": updates})
    event.update(updates)
    ch_id = event.get("channel_id")
    if ch_id:
        match_ch = interaction.guild.get_channel(int(ch_id))
        if match_ch:
            try:
                await match_ch.set_permissions(interaction.user, read_messages=True, send_messages=True,
                                               reason=f"รับหน้าที่ {staff_type}")
            except discord.Forbidden:
                pass
    sched_ch_id = event.get("schedule_channel_id"); msg_id = event.get("message_id")
    if sched_ch_id and msg_id:
        sched_ch = interaction.guild.get_channel(int(sched_ch_id))
        if sched_ch:
            try:
                msg = await sched_ch.fetch_message(int(msg_id))
                await msg.edit(embed=build_schedule_embed(event, interaction.guild))
            except Exception:
                pass
    role_th = "กรรมการ" if staff_type == "judge" else "ผู้บันทึก"
    await interaction.followup.send(f"✅ คุณรับหน้าที่**{role_th}**ในแมตช์นี้แล้ว!", ephemeral=True)

class StaffView(discord.ui.View):
    def __init__(self, event_oid: str, guild_id: int):
        super().__init__(timeout=None)
        self.event_oid = event_oid; self.guild_id = guild_id
        j_btn = discord.ui.Button(label="⚖️  กรรมการ", style=discord.ButtonStyle.primary,
                                   custom_id=f"staff_judge_{guild_id}_{event_oid}")
        j_btn.callback = self._judge_cb
        r_btn = discord.ui.Button(label="🎥  ผู้บันทึก", style=discord.ButtonStyle.secondary,
                                   custom_id=f"staff_recorder_{guild_id}_{event_oid}")
        r_btn.callback = self._recorder_cb
        self.add_item(j_btn); self.add_item(r_btn)
    async def _judge_cb(self, interaction): await handle_staff_click(interaction, self.event_oid, "judge")
    async def _recorder_cb(self, interaction): await handle_staff_click(interaction, self.event_oid, "recorder")

# ── Autocomplete & Transcript ─────────────────────────────────────────────────
async def event_autocomplete(interaction: discord.Interaction, current: str):
    tour = await db.get_active_tour(interaction.guild_id)
    if not tour: return []
    choices = []
    async for ev in db.events_col(interaction.guild_id, tour).find({}, {"title": 1}):
        t = ev.get("title","")
        if current.lower() in t.lower():
            choices.append(app_commands.Choice(name=t, value=t))
        if len(choices) >= 25: break
    return choices

async def log_transcript(interaction: discord.Interaction, cfg: dict, msg: str) -> None:
    try:
        tr_id = cfg.get("transcript_channel")
        if tr_id:
            ch = interaction.guild.get_channel(int(tr_id))
            if ch:
                await ch.send(embed=discord.Embed(description=msg, color=0x95A5A6))
    except Exception:
        pass
