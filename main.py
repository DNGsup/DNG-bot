import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from database import db
from enumOptions import BossName, BroadcastMode, Owner, OWNER_ICONS

from myserver import server_on

intents = discord.Intents.default()
intents.messages = True  # ✅ เปิดการอ่านข้อความ
intents.message_content = True  # ✅ เปิดการเข้าถึงเนื้อหาข้อความ
bot = commands.Bot(command_prefix="!", intents=intents)

# //////////////////////////// event ////////////////////////////
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        bot.tree.clear_commands(guild=None)  # ล้างคำสั่งเก่าก่อน
        synced = await bot.tree.sync()  # ซิงก์คำสั่งใหม่
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")
# //////////////////////////// broadcast ////////////////////////////
async def lock_thread_after_delay(thread: discord.Thread):
    """ล็อกเธรดหลังจาก 24 ชั่วโมง"""
    await asyncio.sleep(86400)
    try:
        await thread.edit(locked=True)
    except discord.NotFound:
        print(f"Thread {thread.name} not found, it might be deleted.")
    except discord.Forbidden:
        print(f"Bot lacks permission to lock thread {thread.name}.")

@app_commands.command(name="broadcast", description="ส่งข้อความบอร์ดแคสต์")
async def broadcast(
    interaction: discord.Interaction,
    mode: BroadcastMode,
    boss_name: BossName,
    date: str,
    hour: int,
    minute: int,
    owner: Owner,
    room: str = None
):
    if not interaction.guild:
        await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"{OWNER_ICONS[owner.value]} ✦～ 𝐁𝐨𝐬𝐬﹕{boss_name.value} 𝐃𝐚𝐭𝐞﹕{date} {hour:02}:{minute:02} ～✦",
        color=discord.Color.blue()
    )

    try:
        if mode == BroadcastMode.STANDARD:
            if not room:
                await interaction.response.send_message("กรุณาเลือกห้อง", ephemeral=True)
                return

            channel = discord.utils.get(interaction.guild.text_channels, name=room.lower())
            if not channel:
                await interaction.response.send_message(f"ไม่พบห้อง `{room}`", ephemeral=True)
                return

            msg = await channel.send(embed=embed)
            thread = await msg.create_thread(name=f"{boss_name.value} Discussion")
            bot.loop.create_task(lock_thread_after_delay(thread))
            await interaction.response.send_message(f"📢 Broadcast sent to {room}", ephemeral=True)

        elif mode == BroadcastMode.MULTI:
            broadcast_rooms = db.get_rooms()

            if not broadcast_rooms:
                await interaction.response.send_message("ไม่มีห้องที่ตั้งค่าไว้สำหรับ Multi Broadcast", ephemeral=True)
                return

            found_channels = [
                discord.utils.get(interaction.guild.text_channels, name=room_name.lower())
                for room_name in broadcast_rooms
            ]
            found_channels = [ch for ch in found_channels if ch]

            if not found_channels:
                await interaction.response.send_message("ไม่พบห้องใด ๆ ที่ตรงกับค่าที่ตั้งไว้", ephemeral=True)
                return

            for channel in found_channels:
                msg = await channel.send(embed=embed)
                thread = await msg.create_thread(name=f"{boss_name.value} Discussion")
                bot.loop.create_task(lock_thread_after_delay(thread))

            await interaction.response.send_message(f"📢 Broadcast sent to {', '.join([ch.name for ch in found_channels])}", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message("เกิดข้อผิดพลาดในการส่งข้อความ", ephemeral=True)
        print(f"Error in broadcast: {e}")

# ------------------------------------------------------------------------------------------
server_on()
bot.run(os.getenv('TOKEN'))
