import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import pytz
import datetime
import random
from datetime import datetime, timedelta
from myserver import server_on
from enumOptions import BroadcastSettingAction ,BroadcastMode ,BossName ,Owner ,OWNER_ICONS
# แยก import ให้ชัดเจน
from database import update_bp_to_sheets
from database import add_broadcast_channel, remove_broadcast_channel, get_rooms
from database import set_notification_room, set_notification_role
from database import broadcast_channels, notification_room, notification_role, boss_notifications
from scheduler import schedule_boss_notifications
from database import bp_data, bp_reactions, bp_summary_room,giveaways ,giveaway_room ,winner_history

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

# //////////////////////////// broadcast ใช้งานได้แล้ว ✅////////////////////////////
async def lock_thread_after_delay(thread: discord.Thread):
    """ล็อกเธรดหลังจาก 24 ชั่วโมง ค่าคือ (86400)"""
    await asyncio.sleep(60)
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
            thread = await msg.create_thread(name=f"📌𝖡𝗈𝗌𝗌 {boss_name.value} 𝖣𝖺𝗍𝖾﹕{date} {hour:02}:{minute:02}")
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
                thread = await msg.create_thread(name=f"📌𝖡𝗈𝗌𝗌 {boss_name.value} 𝖣𝖺𝗍𝖾﹕{date} {hour:02}:{minute:02}")
                bot.loop.create_task(lock_thread_after_delay(thread))

            await interaction.followup.send(f"📢 Broadcast sent to {', '.join([ch.mention for ch in found_channels])}", ephemeral=True)

    except Exception as e:
        await interaction.followup.send("เกิดข้อผิดพลาดในการส่งข้อความ", ephemeral=True)
        print(f"Error in broadcast: {e}")
# //////////////////////////// notifications คำสั่งใช้งานได้แล้ว✅////////////////////////////
# ----------- ระบบตั้งค่าห้องแจ้งเตือนเวลาบอส ✅ -----------
@bot.tree.command(name='noti_room', description='ตั้งค่าช่องสำหรับแจ้งเตือนบอส')
async def noti_room(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild_id  # ✅ แปลงเป็น string เพื่อให้ตรงกับ database
    set_notification_room(guild_id, channel.id)  # ✅ ใช้ฟังก์ชันแทนการกำหนดค่าโดยตรง
    # ✅ ตอบกลับโดยตรง แทนการ defer()
    await interaction.response.send_message(
        f"✅ ตั้งค่าช่อง {channel.mention} เป็นช่องแจ้งเตือนบอสเรียบร้อยแล้ว!", ephemeral=True
    )
# ----------- ตั้งค่า Role ที่ต้องการให้บอทแท็กในการแจ้งเตือนบอส ✅-----------
@bot.tree.command(name="noti_role", description="ตั้งค่า Role สำหรับแจ้งเตือนบอส")
async def noti_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild_id  # ✅ แปลงเป็น string
    set_notification_role(guild_id, role.id)  # ✅ ใช้ฟังก์ชันแทนการกำหนดค่าโดยตรง

    await interaction.response.send_message(
        f"✅ ตั้งค่า Role Notification เป็น <@&{role.id}> เรียบร้อยแล้ว!",
        ephemeral=True
    )
    print(f"[DEBUG] noti_role: {notification_role}")
# ----------- ลบการแจ้งเตือนบอสที่ตั้งค่าไว้ -----------
@bot.tree.command(name="remove_notification", description="ลบการแจ้งเตือนบอสที่ตั้งค่าไว้")
async def remove_notification(interaction: discord.Interaction, boss_name: BossName):
    guild_id = interaction.guild_id  # ใช้ค่า guild_id ปัจจุบัน

    if guild_id not in boss_notifications or not boss_notifications[guild_id]:
        return await interaction.response.send_message("❌ ไม่มีรายการแจ้งเตือนบอส", ephemeral=True)

    before_count = len(boss_notifications[guild_id])
    boss_notifications[guild_id] = [
        notif for notif in boss_notifications[guild_id]
        if notif["boss_name"] != boss_name.name
    ]
    after_count = len(boss_notifications[guild_id])

    if before_count == after_count:
        await interaction.response.send_message(f"❌ ไม่พบการแจ้งเตือนของ {boss_name.value}", ephemeral=True)
    else:
        await interaction.response.send_message(f"✅ ลบการแจ้งเตือนของ {boss_name.value} เรียบร้อยแล้ว!", ephemeral=True)
# ----------- ล้างรายการแจ้งเตือนบอสทั้งหมด ✅ -----------
@bot.tree.command(name="clear_notifications", description="ล้างรายการแจ้งเตือนบอสทั้งหมด")
async def clear_notifications(interaction: discord.Interaction):
    guild_id = interaction.guild_id  # ใช้ค่า guild_id ปัจจุบัน

    if guild_id not in boss_notifications or not boss_notifications[guild_id]:
        return await interaction.response.send_message("❌ ไม่มีข้อมูลให้ล้าง", ephemeral=True)

    boss_notifications[guild_id] = []  # เคลียร์รายการแจ้งเตือนทั้งหมด
    await interaction.response.send_message("✅ ล้างรายการแจ้งเตือนบอสทั้งหมดเรียบร้อยแล้ว!", ephemeral=True)
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
    guild_id = interaction.guild_id  # ✅ แปลงเป็น string
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

    # ✅ แทนที่การลบจริงด้วยการสร้างตัวแปรใหม่เพื่อแสดงผล
    active_notifications = [
        notif for notif in boss_notifications.get(guild_id, [])
        if notif["spawn_time"] > now
    ]
    print(f"[DEBUG] notification_list - Found {len(active_notifications)} active notifications")

    if not active_notifications:
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
        async def announce(self,interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()

            guild_id = interaction.guild_id
            channel_id = notification_room.get(guild_id)

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
# //////////////////////////// check bp คำสั่งใช้งานได้แล้ว✅ ////////////////////////////
@bot.tree.command(name="set_bp", description="ตั้งค่าคะแนน BP ตามอีโมจิ")
async def set_bp(interaction: discord.Interaction, emoji: str, points: int):
    bp_reactions[emoji] = points
    await interaction.response.send_message(f'ตั้งค่าคะแนนให้ {emoji} = {points} BP', ephemeral=True)

@bot.tree.command(name="setting_bproom", description="ตั้งค่าห้องสำหรับสรุปคะแนน")
async def setting_bproom(interaction: discord.Interaction, room: discord.TextChannel):
    bp_summary_room[interaction.guild_id] = room.id
    await interaction.response.send_message(f'ตั้งค่าห้องสรุปคะแนนเป็น {room.mention}', ephemeral=True)


@bot.tree.command()
async def check_bp(interaction: discord.Interaction):
    """ คำนวณคะแนน BP ในเธรดที่พิมพ์คำสั่ง """
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("คำสั่งนี้ต้องใช้ในเธรดเท่านั้น!", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    thread = interaction.channel
    thread_name = thread.name  # ดึงชื่อเธรด
    user_bp = {}

    async for message in thread.history(limit=None):
        if message.author.bot:
            continue

        if message.author.id not in user_bp:
            user_bp[message.author.id] = 0

        for reaction in message.reactions:
            if str(reaction.emoji) in bp_reactions:
                async for user in reaction.users():
                    if user.bot:
                        continue
                    user_bp[message.author.id] += bp_reactions[str(reaction.emoji)]

    sorted_bp = sorted(user_bp.items(), key=lambda x: x[1], reverse=True)
    update_bp_to_sheets(dict(sorted_bp), thread_name) # ✅ ส่งข้อมูลไป Google Sheets พร้อมชื่อเธรด
    embed = discord.Embed(title="🏆 สรุปคะแนน BP", color=discord.Color.gold())

    description = ""
    for idx, (user_id, bp) in enumerate(sorted_bp, 1):
        member = interaction.guild.get_member(user_id)
        mention = member.mention if member else f"<@!{user_id}>"
        description += (f"{idx}. {mention}\n"
                        f"╰ {bp} BP\n")

    embed.description = description.strip()  # ลบช่องว่างท้ายข้อความ
    embed.set_footer(text=thread.name)

    embed.description = description
    embed.set_footer(text=thread.name)

    if interaction.guild_id in bp_summary_room:
        summary_channel = bot.get_channel(bp_summary_room[interaction.guild_id])
        if summary_channel:
            await summary_channel.send(embed=embed)
        else:
            await interaction.response.send_message('ไม่พบห้องที่ตั้งค่าไว้', ephemeral=True)
    else:
        await interaction.response.send_message('ยังไม่มีการตั้งค่าห้องสรุปคะแนน', ephemeral=True)

@bot.tree.command(name="add_bp",description="เพิ่มคะแนน BP ให้สมาชิกในเธรดที่ใช้งานอยู่")
async def add_bp(interaction: discord.Interaction, user: discord.Member, bp: int):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("คำสั่งนี้ต้องใช้ในเธรดเท่านั้น!", ephemeral=True)
        return
    await interaction.response.defer(thinking=True, ephemeral=True)

    thread = interaction.channel
    bp_data[user.id] = bp_data.get(user.id, 0) + bp

    embed = discord.Embed(title="💎 บวกคะแนน BP", description=f"<@!{user.id}> : {bp} BP", color=discord.Color.blue())
    embed.set_footer(text=thread.name)

    if interaction.guild_id in bp_summary_room:
        summary_channel = bot.get_channel(bp_summary_room[interaction.guild_id])
        if summary_channel:
            await summary_channel.send(embed=embed)
        else:
            await interaction.response.send_message('ไม่พบห้องที่ตั้งค่าไว้', ephemeral=True)
    else:
        await interaction.response.send_message('ยังไม่มีการตั้งค่าห้องสรุปคะแนน', ephemeral=True)
# //////////////////////////// Giveaway ////////////////////////////
# ✅ ตั้งค่าห้องสุ่มรางวัล
@bot.tree.command(name="setgiveaway", description="ตั้งค่าห้องสำหรับจัดกิจกรรมสุ่มรางวัล")
async def setgiveaway(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild_id)
    giveaway_room[guild_id] = channel.id
    await interaction.response.send_message(f"✅ ตั้งค่าห้อง {channel.mention} สำหรับกิจกรรมสุ่มรางวัลเรียบร้อย!", ephemeral=True)

@bot.tree.command(name="gcreate", description="สร้างกิจกรรมสุ่มรางวัล")
@app_commands.describe(role="เลือกโรลที่สามารถเข้าร่วมได้", image_url="ใส่ URL รูปภาพสำหรับกิจกรรม")
async def gcreate(interaction: discord.Interaction, role: discord.Role, image_url: str = None):
    if not image_url and interaction.channel.last_message and interaction.channel.last_message.attachments:
        image_url = interaction.channel.last_message.attachments[0].url
    await interaction.response.send_modal(GiveawayModal(interaction, role, image_url or ""))

# ✅ ฟอร์มสร้างกิจกรรมสุ่มรางวัล
class GiveawayModal(discord.ui.Modal, title="สร้างกิจกรรมสุ่มรางวัล"):
    prize = discord.ui.TextInput(label="ชื่อรางวัล", placeholder="ใส่ชื่อรางวัล", required=True)
    amount = discord.ui.TextInput(label="จำนวนรางวัล", placeholder="ใส่จำนวนรางวัล", required=True)
    winners = discord.ui.TextInput(label="จำนวนผู้ชนะ", placeholder="ใส่จำนวนผู้ชนะ", required=True)
    duration = discord.ui.TextInput(label="ระยะเวลา (s/m/h/d)", placeholder="เช่น 30s, 5m, 2h", required=True)
    description = discord.ui.TextInput(label="คำอธิบาย", style=discord.TextStyle.long, required=True)

    def __init__(self, interaction: discord.Interaction, role: discord.Role, image_url: str = None):
        super().__init__()
        self.interaction = interaction
        self.role = role
        self.image_url = image_url

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            winners = int(self.winners.value)
            duration_seconds = parse_duration(self.duration.value)

            if duration_seconds is None or duration_seconds < 30 or duration_seconds > 604800:
                await interaction.response.send_message("ระยะเวลาต้องอยู่ระหว่าง 30 วินาทีถึง 7 วัน (7d)", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("จำนวนรางวัลและจำนวนผู้ชนะต้องเป็นตัวเลข", ephemeral=True)
            return

        start_time = datetime.now(local_tz)
        end_time = start_time + timedelta(seconds=duration_seconds)

        embed = discord.Embed(
            title=f"🎁 {self.prize.value} ({amount} รางวัล)",
            description=self.description.value,
            color=discord.Color.gold()
        )
        embed.add_field(name="🏆 จำนวนผู้ชนะ", value=str(winners), inline=True)
        embed.add_field(name="🛡️ โรลที่เข้าร่วมได้", value=self.role.mention, inline=True)
        embed.add_field(name="⏳ สิ้นสุดใน", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
        embed.add_field(name="👥 จำนวนคนเข้าร่วม", value="0", inline=False)

        embed.set_footer(
            text=f"เริ่ม {start_time.strftime('%d/%m/%y %H:%M')} • จบ {end_time.strftime('%d/%m/%y %H:%M')}")
        if self.image_url:
            embed.set_image(url=self.image_url)

        guild_id = str(interaction.guild_id)
        target_channel = bot.get_channel(giveaway_room.get(guild_id, interaction.channel.id))

        if not target_channel:
            await interaction.response.send_message("❌ ไม่พบห้องสำหรับจัดกิจกรรม!", ephemeral=True)
            return

        view = JoinButton(interaction.channel.id, self.role.id)
        message = await target_channel.send(content="🎉 **กิจกรรมสุ่มรางวัลเริ่มแล้ว!!**", embed=embed, view=view)

        giveaways[interaction.channel.id] = {
            "prize": self.prize.value,
            "amount": amount,
            "winners": winners,
            "entries": [],
            "end_time": end_time,
            "embed": embed,
            "embed_message": message,
            "view": view,
            "role_id": self.role.id,
            "image_url": self.image_url
        }

        await interaction.response.send_message("✅ กิจกรรมเริ่มต้นแล้ว!", ephemeral=True)
        await asyncio.sleep(duration_seconds)
        await end_giveaway(interaction.channel.id)

# ✅ ปุ่มเข้าร่วมกิจกรรม
class JoinButton(discord.ui.View):
    def __init__(self, giveaway_id, role_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.role_id = role_id

    @discord.ui.button(label="เข้าร่วม", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = giveaways.get(self.giveaway_id)
        if not giveaway:
            await interaction.response.send_message("❌ กิจกรรมนี้สิ้นสุดลงแล้ว", ephemeral=True)
            return

        if not any(role.id == self.role_id for role in interaction.user.roles):
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์เข้าร่วมกิจกรรมนี้", ephemeral=True)
            return

        if interaction.user.id in giveaway["entries"]:
            await interaction.response.send_message("⚠️ คุณเข้าร่วมกิจกรรมนี้ไปแล้ว!", ephemeral=True)
            return

        giveaway["entries"].append(interaction.user.id)
        giveaway["embed"].set_field_at(3, name="👥 จำนวนคนเข้าร่วม", value=str(len(giveaway["entries"])), inline=False)
        await giveaway["embed_message"].edit(embed=giveaway["embed"], view=self)

        await interaction.response.send_message("✅ คุณเข้าร่วมกิจกรรมแล้ว!", ephemeral=True)

# ✅ ฟังก์ชันจบกิจกรรม
async def end_giveaway(channel_id):
    giveaway = giveaways.get(channel_id)
    if not giveaway:
        return

    giveaway["embed"].set_field_at(2, name="⏳ สิ้นสุดใน", value="`หมดเวลา`", inline=False)
    await giveaway["embed_message"].edit(embed=giveaway["embed"], view=None)

    if not giveaway["entries"]:
        await giveaway["embed_message"].channel.send("❌ ไม่มีผู้เข้าร่วมเพียงพอสำหรับการจับรางวัล")
        giveaways.pop(channel_id, None)
        return

    # ✅ ลดน้ำหนักคนที่ชนะบ่อย
    weights = [1 / (winner_history.get(entry, 0) + 1) for entry in giveaway["entries"]]
    winners = random.choices(giveaway["entries"], weights=weights,
                            k=min(giveaway["winners"], len(giveaway["entries"])))
    # ✅ อัปเดตประวัติการชนะ
    for winner in winners:
        winner_history[winner] = winner_history.get(winner, 0) + 1

    winner_mentions = ', '.join(f"<@{winner}>" for winner in winners)
    win_embed = discord.Embed(
        title="🎉 ขอแสดงความยินดี! 🎉",
        description=f"{winner_mentions} ได้รับรางวัล {giveaway['prize']}!",
            color=discord.Color.green()
    )
    await giveaway["embed_message"].channel.send(embed=win_embed)
    giveaways.pop(channel_id, None)

# ✅ ฟังก์ชันแปลงเวลา
def parse_duration(duration: str):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        return int(duration[:-1]) * units[duration[-1]]
    except:
        return None
# ------------------------------------------------------------------------------------------
server_on()
bot.run(os.getenv('TOKEN'))
