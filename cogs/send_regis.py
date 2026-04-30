"""
cogs/send_regis.py  — /send_regis
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
import db
from config import COLOR_INFO, COLOR_SUCCESS, REGISTRATION_LOG_CHANNEL_ID

class RegistrationModal(discord.ui.Modal, title="📋 สมัครเข้าร่วมทัวร์นาเมนท์"):
    game_id = discord.ui.TextInput(
        label="ID ในเกม",
        placeholder="วาง ID ในเกมของคุณที่นี่…",
        min_length=4, max_length=80,
    )
    def __init__(self, log_channel_id: int, tour_data: str):
        super().__init__()
        self.log_channel_id = log_channel_id
        self.tour_data = tour_data

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        embed = discord.Embed(title="📋 ผู้สมัครใหม่", color=COLOR_SUCCESS)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ชื่อ Discord",  value=member.name,        inline=True)
        embed.add_field(name="แท็ก Discord",  value=str(member),        inline=True)
        embed.add_field(name="ID Discord",    value=str(member.id),     inline=True)
        embed.add_field(name="ID ในเกม",      value=self.game_id.value, inline=False)
        if self.tour_data:
            embed.add_field(name="ข้อมูลทัวร์", value=self.tour_data, inline=False)
        log_ch = interaction.client.get_channel(self.log_channel_id)
        if log_ch:
            await log_ch.send(embed=embed)
        try:
            tour, _ = await db.require_active(interaction.guild_id)
            col = db.players_col(interaction.guild_id, tour)
            existing = await col.find_one({"discord_id": member.id})
            if existing:
                return await interaction.followup.send(
                    "⚠️ คุณสมัครไปแล้ว! หากต้องการแก้ไขข้อมูลกรุณาติดต่อสตาฟ", ephemeral=True)
            await col.insert_one({
                "discord_id": member.id, "discord_username": member.name,
                "discord_tag": str(member), "game_id": self.game_id.value,
            })
        except Exception:
            pass
        await interaction.followup.send("✅ สมัครเรียบร้อยแล้ว! ขอบคุณที่เข้าร่วม 🎉", ephemeral=True)

class RegisterView(discord.ui.View):
    def __init__(self, log_channel_id: int, tour_data: str):
        super().__init__(timeout=None)
        self.log_channel_id = log_channel_id
        self.tour_data = tour_data

    @discord.ui.button(label="📝  สมัครเลย", style=discord.ButtonStyle.primary, custom_id="tournament_register")
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationModal(self.log_channel_id, self.tour_data))

class SendRegisCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.add_view(RegisterView(REGISTRATION_LOG_CHANNEL_ID, ""))

    @app_commands.command(name="send_regis", description="โพสต์ประกาศรับสมัครทัวร์นาเมนท์พร้อมปุ่มสมัคร")
    @app_commands.describe(
        channel="ช่องที่จะโพสต์ประกาศ",
        data="รายละเอียดทัวร์ที่แสดงใน embed",
        embedded_image="รูปแบนเนอร์โปสเตอร์ทัวร์",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def send_regis(self, interaction: discord.Interaction,
                         channel: discord.TextChannel, data: str,
                         embedded_image: discord.Attachment | None = None) -> None:
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title="📋  เปิดรับสมัครทัวร์นาเมนท์", description=data, color=COLOR_INFO)
        embed.set_footer(text="กดปุ่มด้านล่างเพื่อสมัครเข้าร่วม")
        if embedded_image:
            embed.set_image(url=embedded_image.url)
        view = RegisterView(REGISTRATION_LOG_CHANNEL_ID, data)
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ โพสต์ embed สมัครไปที่ {channel.mention} เรียบร้อยแล้ว", ephemeral=True)
        try:
            _, cfg = await db.require_active(interaction.guild_id)
            tr_id = cfg.get("transcript_channel")
            if tr_id:
                tr_ch = interaction.guild.get_channel(int(tr_id))
                if tr_ch:
                    await tr_ch.send(embed=discord.Embed(
                        description=f"📋 โพสต์รับสมัครใน {channel.mention} โดย {interaction.user.mention}", color=0x95A5A6))
        except Exception:
            pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SendRegisCog(bot))
