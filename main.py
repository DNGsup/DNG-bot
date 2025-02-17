import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import pytz

from myserver import server_on
from enumOptions import BroadcastSettingAction ,BroadcastMode ,BossName ,Owner ,OWNER_ICONS ,NotificationSettingType
from database import add_broadcast_channel, remove_broadcast_channel, get_rooms
from database import set_notification_room ,set_notification_role ,add_boss_notification ,remove_boss_notification ,get_boss_notifications ,get_notification_settings
from scheduler import schedule_boss_notifications ,ConfirmView

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
        asyncio.create_task(schedule_boss_notifications(bot))
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
# //////////////////////////// broadcast ใช้งานได้แล้ว ✅////////////////////////////
async def lock_thread_after_delay(thread: discord.Thread):
    """ล็อกเธรดหลังจาก 24 ชั่วโมง ค่าคือ (86400)"""
    await asyncio.sleep(10)
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
        await interaction.response.send_message(f"✅ เพิ่มห้อง {channel.mention} เข้าสู่รายการบอร์ดแคสต์!",
                                                ephemeral=True)
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
        room: discord.TextChannel = None
):
    if not interaction.guild:
        await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
        return

    embed = discord.Embed(
        title=f" {OWNER_ICONS[owner.value]}・𝐁𝐨𝐬𝐬﹕{boss_name.value} 𝐃𝐚𝐭𝐞﹕{date} {hour:02}:{minute:02} ～✦",
        color=discord.Color.blue()
    )

    try:
        guild_id = str(interaction.guild_id)

        if mode == BroadcastMode.STANDARD:
            if not room:
                await interaction.response.send_message("กรุณาเลือกห้องสำหรับ Standard Broadcast", ephemeral=True)
                return

            msg = await room.send(embed=embed)
            thread = await msg.create_thread(name=f"📌 {boss_name.value} ⤵")
            bot.loop.create_task(lock_thread_after_delay(thread))
            await interaction.response.send_message(f"📢 Broadcast sent to {room.mention}", ephemeral=True)

        elif mode == BroadcastMode.MULTI:
            broadcast_rooms = get_rooms(guild_id)

            if not broadcast_rooms:
                await interaction.response.send_message("ไม่มีห้องที่ตั้งค่าไว้สำหรับ Multi Broadcast", ephemeral=True)
                return

            found_channels = [
                discord.utils.get(interaction.guild.text_channels, id=int(room_id))
                for room_id in broadcast_rooms
            ]
            found_channels = [ch for ch in found_channels if ch]

            if not found_channels:
                await interaction.response.send_message("ไม่พบห้องใด ๆ ที่ตรงกับค่าที่ตั้งไว้", ephemeral=True)
                return

            for channel in found_channels:
                msg = await channel.send(embed=embed)
                thread = await msg.create_thread(name=f"📌 {boss_name.value} ⤵")
                bot.loop.create_task(lock_thread_after_delay(thread))

            await interaction.response.send_message(
                f"📢 Broadcast sent to {', '.join([ch.mention for ch in found_channels])}", ephemeral=True
            )

    except Exception as e:
        await interaction.response.send_message("เกิดข้อผิดพลาดในการส่งข้อความ", ephemeral=True)
        print(f"Error in broadcast: {e}")
# //////////////////////////// notifications ////////////////////////////
local_tz = pytz.timezone("Asia/Bangkok")  # ตั้งค่า Timezone เป็นไทย

@bot.tree.command(name="notifications_setting", description="ตั้งค่าห้อง, โรล และลบบอสจากการแจ้งเตือน")
@app_commands.describe(setting_type="เลือกประเภทการตั้งค่า", value="เลือกค่าที่ต้องการตั้งหรือลบ")
async def notifications_setting(
        interaction: discord.Interaction,
        setting_type: NotificationSettingType,
        value: discord.abc.GuildChannel | discord.Role | BossName
):
    guild_id = str(interaction.guild_id)

    if setting_type == NotificationSettingType.ROOM and isinstance(value, discord.TextChannel):
        set_notification_room(guild_id, value.id)
        await interaction.response.send_message(f"✅ ตั้งค่าห้องแจ้งเตือนเป็น {value.mention}", ephemeral=True)

    elif setting_type == NotificationSettingType.ROLE and isinstance(value, discord.Role):
        set_notification_role(guild_id, value.id)
        await interaction.response.send_message(f"✅ ตั้งค่าโรลแจ้งเตือนเป็น {value.mention}", ephemeral=True)

    elif setting_type == NotificationSettingType.DEL and isinstance(value, BossName):
        remove_boss_notification(guild_id, value.value)
        await interaction.response.send_message(f"✅ ลบการแจ้งเตือนของ {value.value}", ephemeral=True)

    else:
        await interaction.response.send_message("❌ ค่าที่ป้อนไม่ถูกต้อง โปรดตรวจสอบอีกครั้ง", ephemeral=True)

@bot.tree.command(name="notifications", description="เพิ่มการแจ้งเตือนบอส")
@app_commands.describe(boss_name="เลือกบอส", date="เลือกวันที่", hour="เลือกชั่วโมง", minute="เลือกนาที",
                        owner="เลือกเจ้าของ")
async def notifications(
        interaction: discord.Interaction,
        boss_name: BossName,
        date: str,
        hour: int,
        minute: int,
        owner: Owner
):
    guild_id = str(interaction.guild_id)
    settings = get_notification_settings(guild_id)

    if not settings["room"] or not settings["role"]:
        return await interaction.response.send_message("❌ โปรดตั้งค่าห้องและโรลแจ้งเตือนก่อน!", ephemeral=True)

    add_boss_notification(guild_id, boss_name.value, date, hour, minute, owner.value)
    await interaction.response.send_message(
        f"✅ เพิ่มแจ้งเตือน {boss_name.value} วันที่ {date} เวลา {hour:02}:{minute:02}", ephemeral=True
    )

@bot.tree.command(name="lists", description="แสดงรายการแจ้งเตือนบอสทั้งหมด")
async def lists(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    notifications = get_boss_notifications(guild_id)

    if not notifications:
        return await interaction.response.send_message("❌ ไม่มีรายการแจ้งเตือนบอส", ephemeral=True)

    embed = discord.Embed(title="📜 𝐁𝐨𝐬𝐬 𝐒𝐩𝐚𝐰𝐧 𝐋𝐢𝐬𝐭", color=discord.Color.blue())
    for idx, noti in enumerate(notifications, 1):
        embed.add_field(
            name=f"{idx}. 𝐁𝐨𝐬𝐬 ﹕{noti['boss_name']} 𝐎𝐰𝐧𝐞𝐫 ﹕{noti['owner']}",
            value=f"𝐒𝐩𝐚𝐰𝐧 ﹕{noti['date']} {noti['spawn_time']} น.",
            inline=False
        )
    view = ConfirmView(embed, guild_id)
    await interaction.response.send_message(embed=embed, ephemeral=True, view=view)
# ------------------------------------------------------------------------------------------
server_on()
bot.run(os.getenv('TOKEN'))
