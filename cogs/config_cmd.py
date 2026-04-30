"""
cogs/config_cmd.py  — /config set | edit | show | switch
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from config import COLOR_ERROR, COLOR_INFO, COLOR_SUCCESS, COLOR_WARN

def _config_embed(cfg: dict, tour_name: str, guild: discord.Guild) -> discord.Embed:
    def role_str(rid):
        if not rid: return "—"
        r = guild.get_role(int(rid))
        return r.mention if r else f"`@role:{rid}`"
    def ch_str(cid):
        if not cid: return "—"
        c = guild.get_channel(int(cid))
        return c.mention if c else f"`#ช่อง:{cid}`"
    e = discord.Embed(title=f"⚙️  ตั้งค่า — {tour_name}", color=COLOR_INFO)
    e.add_field(name="บทบาทผู้จัดการบอท",      value=role_str(cfg.get("bot_op_role")),         inline=True)
    e.add_field(name="บทบาทกรรมการ",           value=role_str(cfg.get("judge_role")),           inline=True)
    e.add_field(name="บทบาทผู้บันทึก",          value=role_str(cfg.get("recorder_role")),        inline=True)
    e.add_field(name="ช่องตารางแข่ง",           value=ch_str(cfg.get("schedule_channel")),       inline=True)
    e.add_field(name="ช่องผลการแข่งขัน",        value=ch_str(cfg.get("results_channel")),        inline=True)
    e.add_field(name="ช่องแจ้งเตือน",           value=ch_str(cfg.get("notification_channel")),   inline=True)
    e.add_field(name="ช่อง Transcript",         value=ch_str(cfg.get("transcript_channel")),     inline=True)
    e.add_field(name="ช่องภาพ Thumbnail",       value=ch_str(cfg.get("thumbnail_channel")),      inline=True)
    e.add_field(name="โลโก้ทัวร์",              value=cfg.get("tour_logo") or "—",               inline=False)
    e.set_footer(text=f"ทัวร์ที่ใช้งาน: {tour_name}")
    return e

class ConfigCog(commands.Cog):
    config_group = app_commands.Group(
        name="config",
        description="ตั้งค่าทัวร์นาเมนท์",
        default_permissions=discord.Permissions(administrator=True),
    )

    @config_group.command(name="set", description="สร้างทัวร์นาเมนท์ใหม่และบันทึกการตั้งค่าทั้งหมด")
    @app_commands.describe(
        tour_name="ชื่อทัวร์ — ใช้เป็นชื่อฐานข้อมูล MongoDB ด้วย",
        bot_op_role="บทบาทที่จัดการบอทได้ (สร้าง/แก้ไข/ลบ event)",
        judge_role="บทบาทกรรมการ",
        recorder_role="บทบาทผู้บันทึกวิดีโอ",
        schedule_channel="ช่องโพสต์ตารางแข่งขัน",
        results_channel="ช่องโพสต์ผลการแข่งขัน",
        notification_channel="ช่องแจ้งเตือนทั่วไป",
        transcript_channel="ช่องบันทึกกิจกรรมทั้งหมดของบอท",
        thumbnail_channel="ช่องที่เก็บรูป Thumbnail",
        tour_logo="URL รูปโลโก้ทัวร์ขนาดใหญ่",
    )
    async def config_set(self, interaction: discord.Interaction,
                         tour_name: str,
                         bot_op_role: discord.Role, judge_role: discord.Role,
                         recorder_role: discord.Role,
                         schedule_channel: discord.TextChannel,
                         results_channel: discord.TextChannel,
                         notification_channel: discord.TextChannel,
                         transcript_channel: discord.TextChannel,
                         thumbnail_channel: discord.TextChannel,
                         tour_logo: str) -> None:
        await interaction.response.defer(ephemeral=True)
        data = {
            "tour_name": tour_name,
            "bot_op_role": bot_op_role.id, "judge_role": judge_role.id,
            "recorder_role": recorder_role.id,
            "schedule_channel": schedule_channel.id, "results_channel": results_channel.id,
            "notification_channel": notification_channel.id, "transcript_channel": transcript_channel.id,
            "thumbnail_channel": thumbnail_channel.id, "tour_logo": tour_logo,
        }
        col = db.config_col(interaction.guild_id, tour_name)
        await col.delete_many({})
        await col.insert_one(data)
        await db.add_tour(interaction.guild_id, tour_name)
        await db.set_active_tour(interaction.guild_id, tour_name)
        embed = _config_embed(data, tour_name, interaction.guild)
        embed.colour = COLOR_SUCCESS
        embed.set_footer(text=f"✅ สร้างทัวร์ '{tour_name}' และตั้งเป็นทัวร์ที่ใช้งานแล้ว")
        await interaction.followup.send(embed=embed, ephemeral=True)
        log_ch = interaction.guild.get_channel(transcript_channel.id)
        if log_ch:
            await log_ch.send(embed=discord.Embed(
                description=f"🆕 สร้างทัวร์ **{tour_name}** โดย {interaction.user.mention}", color=COLOR_SUCCESS))

    @config_group.command(name="edit", description="แก้ไขการตั้งค่าทัวร์ที่กำลังใช้งาน")
    @app_commands.describe(
        bot_op_role="บทบาทผู้จัดการบอท", judge_role="บทบาทกรรมการ",
        recorder_role="บทบาทผู้บันทึก", schedule_channel="ช่องตารางแข่ง",
        results_channel="ช่องผลแข่งขัน", notification_channel="ช่องแจ้งเตือน",
        transcript_channel="ช่อง Transcript", thumbnail_channel="ช่อง Thumbnail",
        tour_logo="URL โลโก้ทัวร์ใหม่",
    )
    async def config_edit(self, interaction: discord.Interaction,
                          bot_op_role: discord.Role | None = None,
                          judge_role: discord.Role | None = None,
                          recorder_role: discord.Role | None = None,
                          schedule_channel: discord.TextChannel | None = None,
                          results_channel: discord.TextChannel | None = None,
                          notification_channel: discord.TextChannel | None = None,
                          transcript_channel: discord.TextChannel | None = None,
                          thumbnail_channel: discord.TextChannel | None = None,
                          tour_logo: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)
        updates: dict = {}
        if bot_op_role:           updates["bot_op_role"]          = bot_op_role.id
        if judge_role:            updates["judge_role"]            = judge_role.id
        if recorder_role:         updates["recorder_role"]         = recorder_role.id
        if schedule_channel:      updates["schedule_channel"]      = schedule_channel.id
        if results_channel:       updates["results_channel"]       = results_channel.id
        if notification_channel:  updates["notification_channel"]  = notification_channel.id
        if transcript_channel:    updates["transcript_channel"]    = transcript_channel.id
        if thumbnail_channel:     updates["thumbnail_channel"]     = thumbnail_channel.id
        if tour_logo is not None: updates["tour_logo"]             = tour_logo
        if not updates:
            return await interaction.followup.send("⚠️ ไม่มีการเปลี่ยนแปลง — ทุกช่องยังว่างอยู่", ephemeral=True)
        col = db.config_col(interaction.guild_id, tour)
        await col.update_one({}, {"$set": updates})
        new_cfg = await col.find_one({}, {"_id": 0})
        embed = _config_embed(new_cfg, tour, interaction.guild)
        embed.set_footer(text="✅ แก้ไขการตั้งค่าเรียบร้อยแล้ว")
        await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            tr_id = new_cfg.get("transcript_channel")
            if tr_id:
                tr_ch = interaction.guild.get_channel(int(tr_id))
                if tr_ch:
                    fields = ", ".join(f"`{k}`" for k in updates)
                    await tr_ch.send(embed=discord.Embed(
                        description=f"✏️ แก้ไขตั้งค่าโดย {interaction.user.mention} | เปลี่ยน: {fields}",
                        color=COLOR_WARN))
        except Exception:
            pass

    @config_group.command(name="show", description="แสดงการตั้งค่าของทัวร์ที่กำลังใช้งาน")
    async def config_show(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as e:
            return await interaction.followup.send(f"❌ {e}", ephemeral=True)
        await interaction.followup.send(embed=_config_embed(cfg, tour, interaction.guild), ephemeral=True)

    @config_group.command(name="switch", description="เปลี่ยนไปใช้ทัวร์ที่สร้างไว้ก่อนหน้า")
    @app_commands.describe(tour_name="ชื่อทัวร์ที่ต้องการเปลี่ยน")
    async def config_switch(self, interaction: discord.Interaction, tour_name: str) -> None:
        await interaction.response.defer(ephemeral=True)
        tours = await db.list_tours(interaction.guild_id)
        if tour_name not in tours:
            opts = ", ".join(f"`{t}`" for t in tours) if tours else "ยังไม่มีทัวร์"
            return await interaction.followup.send(
                f"❌ ไม่พบทัวร์ `{tour_name}` | ทัวร์ที่มี: {opts}", ephemeral=True)
        await db.set_active_tour(interaction.guild_id, tour_name)
        cfg = await db.config_col(interaction.guild_id, tour_name).find_one({}, {"_id": 0})
        embed = _config_embed(cfg or {}, tour_name, interaction.guild)
        embed.set_footer(text=f"✅ เปลี่ยนไปใช้ทัวร์ '{tour_name}' แล้ว")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @config_switch.autocomplete("tour_name")
    async def tour_name_autocomplete(self, interaction: discord.Interaction, current: str):
        tours = await db.list_tours(interaction.guild_id)
        return [app_commands.Choice(name=t, value=t) for t in tours if current.lower() in t.lower()][:25]

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConfigCog(bot))
