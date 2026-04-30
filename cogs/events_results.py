"""
cogs/events_results.py  — /events results
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from utils.events_helpers import build_results_embed, event_autocomplete, has_op_role, log_transcript, utc_str
from utils.image_gen import generate_match_card, get_latest_channel_image

class EventsResultsCog(commands.Cog):
    from cogs.events_group import events_group
    def __init__(self, bot): self.bot = bot

    @events_group.command(name="results", description="โพสต์ผลการแข่งขันไปที่ช่องผลการแข่ง")
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
    async def events_results(self, interaction: discord.Interaction,
                             event: str, team1_score: str, team2_score: str,
                             number_of_matches: int | None=None, remarks: str | None=None,
                             rec_link: str | None=None,
                             screenshot1: discord.Attachment | None=None, screenshot2: discord.Attachment | None=None,
                             screenshot3: discord.Attachment | None=None, screenshot4: discord.Attachment | None=None,
                             screenshot5: discord.Attachment | None=None, screenshot6: discord.Attachment | None=None,
                             screenshot7: discord.Attachment | None=None, screenshot8: discord.Attachment | None=None,
                             screenshot9: discord.Attachment | None=None) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            active_tour, cfg = await db.require_active(interaction.guild_id)
        except ValueError as exc:
            return await interaction.followup.send(f"❌ {exc}", ephemeral=True)
        if not has_op_role(interaction.user, cfg):
            return await interaction.followup.send("❌ คุณต้องมีบทบาทผู้จัดการบอท", ephemeral=True)
        col       = db.events_col(interaction.guild_id, active_tour)
        event_doc = await col.find_one({"title": event})
        if not event_doc:
            return await interaction.followup.send(f"❌ ไม่พบ event `{event}`", ephemeral=True)
        shots = [att.url for att in [screenshot1,screenshot2,screenshot3,screenshot4,screenshot5,
                                     screenshot6,screenshot7,screenshot8,screenshot9] if att]
        result_doc = {"event_title": event, "team1_score": team1_score, "team2_score": team2_score,
                      "number_of_matches": number_of_matches, "remarks": remarks,
                      "rec_link": rec_link, "screenshots": shots}
        res_ch_id = cfg.get("results_channel")
        res_ch    = interaction.guild.get_channel(int(res_ch_id)) if res_ch_id else None
        if not res_ch:
            return await interaction.followup.send("❌ ยังไม่ได้ตั้ง `ช่องผลการแข่ง` ใน /config set", ephemeral=True)
        if len(shots) > 1:
            for i in range(0, len(shots[1:]), 5):
                await res_ch.send(content="\n".join(shots[1:][i:i+5]))
        logo_url  = cfg.get("tour_logo"); thumb_url = None
        tc = cfg.get("thumbnail_channel")
        if tc: thumb_url = await get_latest_channel_image(self.bot, int(tc))
        t1 = event_doc.get("captain1_name") or event_doc.get("team1","ทีม 1")
        t2 = event_doc.get("captain2_name") or event_doc.get("team2","ทีม 2")
        card_buf  = await generate_match_card(team1=t1, team2=t2, time_str=utc_str(event_doc),
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
    await bot.add_cog(EventsResultsCog(bot))
