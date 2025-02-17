import os
import discord
from discord.ext import commands
from discord import app_commands
from database import db
import asyncio

from myserver import server_on
from enumOptions import BroadcastSettingAction ,BroadcastMode ,BossName ,Owner ,OWNER_ICONS
from database import add_broadcast_channel, remove_broadcast_channel

intents = discord.Intents.default()
intents.messages = True  # ✅ เปิดการอ่านข้อความ
intents.message_content = True  # ✅ เปิดการเข้าถึงเนื้อหาข้อความ
bot = commands.Bot(command_prefix="!", intents=intents)

# //////////////////////////// event ////////////////////////////
@bot.event
async def on_ready():
    print("Bot Online!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
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
        
@bot.tree.command(name="broadcast_setting", description="ตั้งค่าห้องบอร์ดแคสต์")
@app_commands.describe(
    action="เลือกการกระทำ (Add หรือ Remove)",
    channel="เลือกห้องที่ต้องการตั้งค่า"
)
async def broadcast_setting(
    interaction: discord.Interaction,
    action: BroadcastSettingAction,
    channel: discord.TextChannel
):
    guild_id = str(interaction.guild_id)

    if action == BroadcastSettingAction.ADD:
        add_broadcast_channel(guild_id, channel.id)
        await interaction.response.send_message(f"✅ เพิ่มห้อง {channel.mention} เข้าสู่รายการบอร์ดแคสต์!", ephemeral=True)

    elif action == BroadcastSettingAction.REMOVE:
        remove_broadcast_channel(guild_id, channel.id)
        await interaction.response.send_message(f"✅ ลบห้อง {channel.mention} ออกจากรายการบอร์ดแคสต์!", ephemeral=True)

@bot.tree.command(name="broadcast", description="ส่งข้อความบอร์ดแคสต์")
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
