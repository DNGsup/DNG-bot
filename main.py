import os
import asyncio  # ใช้สำหรับหน่วงเวลา
import discord
from discord import app_commands
from discord.ext import commands
from database import db
from enumOptions import BossName, BroadcastMode, Owner, OWNER_ICONS

from myserver import server_on

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# //////////////////////////// event ////////////////////////////
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")
# //////////////////////////// broadcast ////////////////////////////
async def lock_thread_after_delay(thread: discord.Thread):
    """ล็อกเธรดหลังจาก 24 ชั่วโมง"""
    await asyncio.sleep(86400)  # รอ 24 ชั่วโมง
    await thread.edit(locked=True)

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
    embed = discord.Embed(
        title=f"{OWNER_ICONS[owner.value]} ✦～ 𝐁𝐨𝐬𝐬﹕{boss_name.value} 𝐃𝐚𝐭𝐞﹕{date} {hour:02}:{minute:02} ～✦",
        color=discord.Color.blue()
    )

    if mode == BroadcastMode.STANDARD:
        if not room:
            await interaction.response.send_message("กรุณาเลือกห้อง", ephemeral=True)
            return

        channel = discord.utils.get(interaction.guild.text_channels, name=room)
        if not channel:
            await interaction.response.send_message(f"ไม่พบห้อง `{room}`", ephemeral=True)
            return

        msg = await channel.send(embed=embed)
        thread = await msg.create_thread(name=f"{boss_name.value} Discussion")
        bot.loop.create_task(lock_thread_after_delay(thread))  # ✅ ล็อกเธรดหลัง 24 ชม.
        await interaction.response.send_message(f"📢 Broadcast sent to {room}", ephemeral=True)


    elif mode == BroadcastMode.MULTI:

        broadcast_rooms = db.get_rooms()

        if not broadcast_rooms:
            await interaction.response.send_message("ไม่มีห้องที่ตั้งค่าไว้สำหรับ Multi Broadcast", ephemeral=True)

            return

        for room_name in broadcast_rooms:

            channel = discord.utils.get(interaction.guild.text_channels, name=room_name)

            if channel:
                msg = await channel.send(embed=embed)

                thread = await msg.create_thread(name=f"{boss_name.value} Discussion")

                bot.loop.create_task(lock_thread_after_delay(thread))  # ✅ ล็อกเธรดหลัง 24 ชม.

        await interaction.response.send_message(f"📢 Broadcast sent to {', '.join(broadcast_rooms)}", ephemeral=True)

# ------------------------------------------------------------------------------------------
server_on()
# เริ่มรันบอท
bot.run(os.getenv('TOKEN'))