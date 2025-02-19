import discord
from discord.ext import commands

import pytz
import datetime
import asyncio
from database import notification_room, notification_role, boss_notifications# แยก import ให้ชัดเจน
from enumOptions import BossName ,OWNER_ICONS ,Owner

local_tz = pytz.timezone('Asia/Bangkok')  # ใช้เวลาประเทศไทย

async def schedule_boss_notifications(bot,guild_id, boss_name, spawn_time, owner, role):
    now = datetime.datetime.now(local_tz)
    intents = discord.Intents.default()
    intents.messages = True  # ✅ เปิดการอ่านข้อความ
    intents.message_content = True  # ✅ เปิดการเข้าถึงเนื้อหาข้อความ
    notification_role[guild_id] = role.id  # บันทึก role.id ลง dictionary
    boss_display_name = BossName[boss_name].value
    time_until_spawn = (spawn_time - now).total_seconds()
    time_before_five_min = max(time_until_spawn - 300, 0)

    if isinstance(owner, str):
        try:
            owner_enum = Owner[owner]  # แปลง string เป็น Enum
        except KeyError:
            owner_enum = None  # หรือค่าดีฟอลต์ที่เหมาะสม
    else:
        owner_enum = owner  # ถ้าเป็น Enum อยู่แล้วก็ใช้เลย
    owner_icon = OWNER_ICONS.get(owner_enum.value if owner_enum else "Unknown", "❓")

    print(f"[DEBUG] Scheduling boss: {boss_name} at {spawn_time} (in {time_until_spawn}s)")

    if time_before_five_min > 0:  # รอ 5 นาทีก่อนบอสเกิด
        await asyncio.sleep(time_before_five_min)

    if guild_id in notification_room:
        channel_id = notification_room[guild_id]
        channel = bot.get_channel(channel_id) or bot.get_channel(int(channel_id))

        if channel:
            embed = discord.Embed(
                title="𝐁𝐨𝐬𝐬 𝐍𝐨𝐭𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧!!",
                description=f"{owner_icon} 𝐁𝐨𝐬𝐬 {boss_display_name} 𝐢𝐬 𝐬𝐩𝐚𝐰𝐧𝐢𝐧𝐠 𝐢𝐧 𝟓 𝐦𝐢𝐧𝐮𝐭𝐞𝐬! <@&{role.id}>",
                color=discord.Color.yellow()
            )
            await channel.send(embed=embed)

    await asyncio.sleep(300)  # รอจนถึงเวลาบอสเกิด
    if guild_id in notification_room:
        channel_id = notification_room[guild_id]
        channel = bot.get_channel(channel_id) or bot.get_channel(int(channel_id))
        if channel:
            embed = discord.Embed(
                title="𝐁𝐨𝐬𝐬 𝐡𝐚𝐬 𝐬𝐩𝐚𝐰𝐧!!",
                description=f"{owner_icon} 𝐁𝐨𝐬𝐬 {boss_display_name} 𝐡𝐚𝐬 𝐒𝐩𝐚𝐰𝐧 𝐋𝐞𝐭'𝐬 𝐟𝐢𝐠𝐡𝐭! <@&{role.id}>",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

local_tz = pytz.timezone("Asia/Bangkok")  # ตั้งเวลาเป็นไทย
# ///////////////////////////////////////////////////////////