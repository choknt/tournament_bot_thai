"""
cogs/events_group.py — กำหนด group คำสั่ง /events ที่ใช้ร่วมกัน
"""
from discord import app_commands

events_group = app_commands.Group(
    name="events",
    description="จัดการ event การแข่งขันทัวร์นาเมนท์",
)
