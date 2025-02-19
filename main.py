import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import pytz
import datetime
from myserver import server_on
from enumOptions import BroadcastSettingAction ,BroadcastMode ,BossName ,Owner ,OWNER_ICONS
from database import add_broadcast_channel, remove_broadcast_channel, get_rooms
from database import set_notification_room, set_notification_role
from database import broadcast_channels, notification_room, notification_role, boss_notifications # แยก import ให้ชัดเจน
from scheduler import schedule_boss_notifications

intents = discord.Intents.default()
intents.messages = True  # ✅ เปิดการอ่านข้อความ
intents.message_content = True  # ✅ เปิดการเข้าถึงเนื้อหาข้อความ
bot = commands.Bot(command_prefix="!", intents=intents)
local_tz = pytz.timezone('Asia/Bangkok')  # ใช้เวลาประเทศไทย
# //////////////////////////// event ////////////////////////////
@bot.event
async def on_ready():
    print("Bot Online!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
# //////////////////////////// คำสั่งดูตั้งค่าของเซิร์ฟเวอร์ ////////////////////////////
@bot.tree.command(name="server_settings", description="ดูการตั้งค่าของเซิร์ฟเวอร์")
async def server_settings(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)

    # ดึงข้อมูลของเซิร์ฟเวอร์นี้
    broadcast_channels_list = broadcast_channels.get(guild_id, [])
    notification_room_id = notification_room.get(guild_id)
    notification_role_id = notification_role.get(guild_id)

    # แปลง broadcast channels ให้เป็นข้อความ รองรับหลายช่อง
    broadcast_channels_text = "\n".join([f"<#{channel_id}>" for channel_id in broadcast_channels_list]) if broadcast_channels_list else "❌ ไม่มีการตั้งค่าห้องบอร์ดแคสต์"
    notification_room_text = f"<#{notification_room_id}>" if notification_room_id else "❌ ยังไม่ได้ตั้งค่าห้องแจ้งเตือนบอส"
    notification_role_text = f"<@&{notification_role_id}>" if notification_role_id else "❌ ยังไม่ได้ตั้งค่า Role แจ้งเตือนบอส"

    # Embed ข้อมูล
    embed = discord.Embed(title="⚙️ Server Settings", color=discord.Color.blue())
    embed.add_field(name="📢 Broadcast Channels", value=broadcast_channels_text, inline=False)
    embed.add_field(name="🔔 Notification Room", value=notification_room_text, inline=False)
    embed.add_field(name="👥 Notification Role", value=notification_role_text, inline=False)

    # ส่ง embed กลับ
    await interaction.response.send_message(embed=embed, ephemeral=True)
# //////////////////////////// broadcast ใช้งานได้แล้ว ✅////////////////////////////
async def lock_thread_after_delay(thread: discord.Thread):
    """ล็อกเธรดหลังจาก 24 ชั่วโมง ค่าคือ (86400)"""
    await asyncio.sleep(10)
    try:
        await thread.edit(locked=True)
    except discord.NotFound:
        print(f"Thread {thread.name} not found, it might be deleted.")
    except discord.Forbidden:
        print(f"❌ Bot ไม่มีสิทธิ์ในการล็อกเธรด {thread.name}. กรุณาให้สิทธิ์ 'Manage Threads'")

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
        await interaction.followup.send("คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์เท่านั้น", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)  # ✅ ป้องกัน Interaction หมดอายุ

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
            await interaction.followup.send(f"📢 Broadcast sent to {room.mention}", ephemeral=True)

        elif mode == BroadcastMode.MULTI:
            broadcast_rooms = get_rooms(guild_id)

            if not broadcast_rooms:
                await interaction.followup.send("ไม่มีห้องที่ตั้งค่าไว้สำหรับ Multi Broadcast", ephemeral=True)
                return

            found_channels = [
                discord.utils.get(interaction.guild.text_channels, id=int(room_id))
                for room_id in broadcast_rooms
            ]
            found_channels = [ch for ch in found_channels if ch]

            if not found_channels:
                await interaction.followup.send("ไม่พบห้องใด ๆ ที่ตรงกับค่าที่ตั้งไว้", ephemeral=True)
                return

            for channel in found_channels:
                msg = await channel.send(embed=embed)
                thread = await msg.create_thread(name=f"📌 {boss_name.value} ⤵")
                bot.loop.create_task(lock_thread_after_delay(thread))

            await interaction.followup.send(f"📢 Broadcast sent to {', '.join([ch.mention for ch in found_channels])}", ephemeral=True)

    except Exception as e:
        await interaction.followup.send("เกิดข้อผิดพลาดในการส่งข้อความ", ephemeral=True)
        print(f"Error in broadcast: {e}")
# //////////////////////////// notifications ////////////////////////////
# ----------- ระบบตั้งค่าห้องแจ้งเตือนเวลาบอส ✅ -----------
@bot.tree.command(name='noti_room', description='ตั้งค่าช่องสำหรับแจ้งเตือนบอส')
async def noti_room(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild_id)  # ✅ แปลงเป็น string เพื่อให้ตรงกับ database
    set_notification_room(guild_id, channel.id)  # ✅ ใช้ฟังก์ชันแทนการกำหนดค่าโดยตรง
    # ✅ ตอบกลับโดยตรง แทนการ defer()
    await interaction.response.send_message(
        f"✅ ตั้งค่าช่อง {channel.mention} เป็นช่องแจ้งเตือนบอสเรียบร้อยแล้ว!", ephemeral=True
    )
# ----------- ตั้งค่า Role ที่ต้องการให้บอทแท็กในการแจ้งเตือนบอส ✅-----------
@bot.tree.command(name="noti_role", description="ตั้งค่า Role สำหรับแจ้งเตือนบอส")
async def noti_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = str(interaction.guild_id)  # ✅ แปลงเป็น string
    set_notification_role(guild_id, role.id)  # ✅ ใช้ฟังก์ชันแทนการกำหนดค่าโดยตรง

    await interaction.response.send_message(
        f"✅ ตั้งค่า Role Notification เป็น <@&{role.id}> เรียบร้อยแล้ว!",
        ephemeral=True
    )
    print(f"[DEBUG] noti_role: {notification_role}")
# ----------- ระบบแจ้งเตือนเวลาบอส ✅-----------
@bot.tree.command(name='notification', description='ตั้งค่าแจ้งเตือนบอส')
async def notification(
        interaction: discord.Interaction,
        boss_name: BossName,
        hours: int,
        minutes: int,
        owner: Owner,
        role: discord.Role = None  # ทำให้ role เป็น optional
):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)  # ✅ แปลงเป็น string

    # ดึง role จาก database ถ้าไม่มีให้ใช้ค่าที่ส่งมา
    role_id = notification_role.get(guild_id)  # ✅ ดึงค่า Role จาก database
    if role is None and role_id:
        role = interaction.guild.get_role(role_id)  # ดึง role object

    # ถ้าไม่มี role เลย ให้แท็ก @everyone แทน
    role_mention = f"<@&{role_id}>" if role else "@everyone"

    now = datetime.datetime.now(local_tz)  # ✅ ใช้ timezone ที่กำหนด
    spawn_time = now + datetime.timedelta(hours=hours, minutes=minutes)

    if guild_id not in boss_notifications:
        boss_notifications[guild_id] = []

    boss_notifications[guild_id].append({
        "boss_name": boss_name.name,
        "spawn_time": spawn_time,
        "owner": owner,
        "role": role_id if role else None  # ป้องกัน NoneType
    })

    await interaction.followup.send(
        f"ตั้งค่าแจ้งเตือนบอส {boss_name.value} เรียบร้อยแล้ว! จะเกิดในอีก {hours} ชั่วโมง {minutes} นาที. {role_mention}",
        ephemeral=True
    )
    # เรียกใช้ฟังก์ชันโดยส่ง bot ไปด้วย
    await schedule_boss_notifications(bot, guild_id, boss_name.name, spawn_time, owner.name, role)
#-------- คำสั่งดูรายการบอสที่ตั้งค่าไว้ ✅-----------
@bot.tree.command(name="notification_list", description="ดูรายการบอสที่ตั้งค่าแจ้งเตือน")
async def notification_list(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)  # ลดดีเลย์จากการ defer

    guild_id = interaction.guild_id
    now = datetime.datetime.now(local_tz)

    # ✅ ลบรายการบอสที่เกิดไปแล้ว
    if guild_id in boss_notifications:
        # ลบการแจ้งเตือนบอสที่ spawn_time ผ่านมาแล้ว
        boss_notifications[guild_id] = [
            notif for notif in boss_notifications[guild_id]
            if notif["spawn_time"] > now  # เก็บเฉพาะรายการที่ยังไม่เกิด
        ]

    if guild_id not in boss_notifications or not boss_notifications[guild_id]:
        return await interaction.followup.send("❌ ไม่มีบอสที่ถูกตั้งค่าแจ้งเตือน", ephemeral=True)

    sorted_notifications = sorted(boss_notifications[guild_id], key=lambda x: x["spawn_time"])

    embed = discord.Embed(title="📜 𝐁𝐨𝐬𝐬 𝐒𝐩𝐚𝐰𝐧 𝐋𝐢𝐬𝐭", color=discord.Color.blue())

    for idx, notif in enumerate(sorted_notifications[:10], start=1):  # จำกัดสูงสุด 10 รายการ
        boss_name = notif["boss_name"].replace("_", " ")
        spawn_time = notif["spawn_time"].astimezone(local_tz).strftime("%H:%M")
        owner = notif["owner"]
        embed.add_field(name=f"{idx}. 𝐁𝐨𝐬𝐬 ﹕{boss_name} | 𝐒𝐩𝐚𝐰𝐧 ﹕{spawn_time} | 𝐎𝐰𝐧𝐞𝐫 ﹕{owner}",
                        value="\u200b",  # ช่องว่าง (zero-width space) เพื่อให้ embed ดูดี
                        inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

    # ✅ ปุ่ม "ประกาศ"
    class ConfirmView(discord.ui.View):
        def __init__(self, embed_data):  # เปลี่ยนชื่อ parameter
            super().__init__(timeout=60)
            self.embed = embed_data  # ✅ ใช้ self.embed

        @discord.ui.button(label="📢 ประกาศ", style=discord.ButtonStyle.green)
        async def announce(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()

            guild_id = interaction.guild_id
            channel_id = notification_room.get(str(guild_id))  # ✅ ใช้ string key

            if not channel_id:
                return await interaction.followup.send("❌ ยังไม่ได้ตั้งค่าช่องแจ้งเตือนบอส!", ephemeral=True)

            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                return await interaction.followup.send("❌ ไม่พบช่องแจ้งเตือน!", ephemeral=True)

            # ✅ ดึง Role ที่ต้องแท็ก
            role_id = notification_role.get(guild_id)
            role_mention = f"<@&{role_id}>" if role_id else "@everyone"

            await channel.send(f"📢 **【𝐓𝐢𝐦𝐞 𝐢𝐧 𝐠𝐚𝐦𝐞 + 𝟏𝐡𝐫】** {role_mention}", embed=self.embed)
            await interaction.followup.send("✅ ประกาศไปที่ห้องแจ้งเตือนเรียบร้อย!", ephemeral=True)

    await interaction.followup.send(embed=embed, ephemeral=True, view=ConfirmView(embed))  # ✅ ส่ง Embed ไปพร้อมปุ่ม
# ------------------------------------------------------------------------------------------
server_on()
bot.run(os.getenv('TOKEN'))