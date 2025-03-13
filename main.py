import os
import re  # ✅ เพิ่ม import re สำหรับ regex
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import pytz
import random
from datetime import datetime, timedelta
from myserver import server_on
from enumOptions import BroadcastSettingAction ,BroadcastMode ,BossName ,Owner ,OWNER_ICONS ,PointType
# แยก import ให้ชัดเจน
from database import extract_number_from_nickname  # ✅ เรียกใช้จาก database.py
from database import update_points_to_sheets
from database import add_broadcast_channel, remove_broadcast_channel, get_rooms
from database import bp_data, bp_reactions, bp_summary_room, wp_summary_room, wp_reactions, wp_data
from database import giveaways ,giveaway_room ,winner_history

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
# //////////////////////////// ดูค่าตั้งค่าของบอท ////////////////////////////
# //////////////////////////// ฟังก์ชันแปลง "1m", "1h", หรือ "1d" เป็น timedelta
def convert_to_timedelta(time_str):
    if "m" in time_str:
        return timedelta(minutes=int(time_str.replace("m", "")))
    elif "h" in time_str:
        return timedelta(hours=int(time_str.replace("h", "")))
    elif "d" in time_str:
        return timedelta(days=int(time_str.replace("d", "")))
    return timedelta(hours=0)  # ค่าเริ่มต้น
# //////////////////////////// broadcast ใช้งานได้แล้ว ✅////////////////////////////
async def lock_thread_after_delay(thread: discord.Thread):
    """ล็อกเธรดหลังจาก 24 ชั่วโมง พร้อมส่งข้อความแจ้งเตือนก่อนปิด [24 ชั่วโมง ค่าคือ (86400)]"""
    await asyncio.sleep(86400)  # รอ 24 ชั่วโมง

    try:
        # ส่งข้อความแจ้งเตือนก่อนปิดเธรด
        await thread.send("❌ หมดเวลาลงรูปแล้ว! เธรดนี้จะถูกปิด")
        # ล็อกเธรด
        await thread.edit(locked=True)

    except discord.NotFound:
        print(f"Thread {thread.name} not found, it might be deleted.")
    except discord.Forbidden:
        print(f"❌ Bot ไม่มีสิทธิ์ในการล็อกเธรด {thread.name}. กรุณาให้สิทธิ์ 'Manage Threads'")
# ////////////////////////////////////////////////////////////////////////////////////
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

# //////////////////////////// check bp คำสั่งใช้งานได้แล้ว✅ ////////////////////////////
# //////////////////////////// setting_room (เปลี่ยนจาก setting_bproom)
@bot.tree.command(name="setting_room", description="ตั้งค่าห้องสำหรับสรุปคะแนน BP หรือ WP")
async def setting_room(interaction: discord.Interaction, options: PointType, room: discord.TextChannel):
    if options == PointType.BP:
        bp_summary_room[interaction.guild_id] = room.id
        await interaction.response.send_message(f'ตั้งค่าห้องสรุป BP เป็น {room.mention}', ephemeral=True)
    else:
        wp_summary_room[interaction.guild_id] = room.id
        await interaction.response.send_message(f'ตั้งค่าห้องสรุป WP เป็น {room.mention}', ephemeral=True)

# ✅ ฟังก์ชันส่ง embed สรุปคะแนนไปยังห้องสรุป BP
def send_summary_embed(guild_id: int, options: PointType):
    if options == PointType.BP:
        summary_channel = bp_summary_room.get(guild_id)
    else:
        summary_channel = wp_summary_room.get(guild_id)
    if not summary_channel:
        return None
    return bot.get_channel(summary_channel)
# //////////////////////////// checkpoints (เปลี่ยนจาก check_bp) ////////////////////////////
@bot.tree.command(name="checkpoints", description="คำนวณคะแนน BP หรือ WP ในเธรดที่พิมพ์คำสั่ง")
async def checkpoints(interaction: discord.Interaction, options: PointType):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("คำสั่งนี้ต้องใช้ในเธรดเท่านั้น!", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    thread = interaction.channel
    thread_name = thread.name
    user_points = {}

    async for message in thread.history(limit=None):
        if message.author.bot:
            continue

        member = await interaction.guild.fetch_member(message.author.id)
        raw_nickname = member.display_name if member else message.author.name
        nickname_number = extract_number_from_nickname(raw_nickname)
        print(f"🔍 ตรวจสอบชื่อ: UserID={message.author.id}, Raw Nickname={raw_nickname}, Extracted={nickname_number}")

        if message.author.id not in user_points:
            user_points[message.author.id] = (nickname_number, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # นับคะแนนจากประเภทอีโมจิที่เลือก
        if options == PointType.BP:
            reactions = set(str(reaction.emoji) for reaction in message.reactions if str(reaction.emoji) in bp_reactions)
            total_points = sum(bp_reactions[emoji] for emoji in reactions)
        else:
            reactions = set(str(reaction.emoji) for reaction in message.reactions if str(reaction.emoji) in wp_reactions)
            total_points = sum(wp_reactions[emoji] for emoji in reactions)

        if total_points > 0:
            user_points[message.author.id] = (
                nickname_number,
                user_points[message.author.id][1] + total_points,  # บวกคะแนนรวม
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

    sorted_points = sorted(user_points.items(), key=lambda x: x[1][1], reverse=True)

    if sorted_points:
        update_points_to_sheets(user_points, thread_name, interaction.guild, options=options, transaction_type="deposit")

    embed = discord.Embed(title=f"🏆 สรุปคะแนน {options.value}", color=discord.Color.gold())
    description = ""
    for idx, (user_id, (username, points, _)) in enumerate(sorted_points, 1):
        member = interaction.guild.get_member(user_id)  # ✅ ดึงข้อมูลสมาชิกจากเซิร์ฟเวอร์
        mention = member.mention if member else f"<@{user_id}>"
        description += f"{mention}\n╰ {points} {options.value}\n\n"
    embed.description = description.strip()
    embed.set_footer(text=thread.name)

    summary_channel = send_summary_embed(interaction.guild_id, options)  # ส่งข้อมูลไปยังห้องสรุปตามประเภทคะแนน
    if summary_channel:
        await summary_channel.send(embed=embed)
        await interaction.followup.send(f"✅ ส่งสรุปคะแนน {options.value} ไปยังห้องสรุปเรียบร้อยแล้ว!", ephemeral=True)
    else:
        await interaction.followup.send(f"⚠️ ไม่พบห้องสรุป {options.value} ที่ตั้งค่าไว้!", ephemeral=True)
# //////////////////////////// addpoints (เปลี่ยนจาก add_bp) ////////////////////////////
@bot.tree.command(name="addpoints", description="เพิ่มคะแนน BP หรือ WP ให้สมาชิกในเธรดที่ใช้งานอยู่")
async def addpoints(interaction: discord.Interaction, options: PointType, user: discord.Member, points: int):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("คำสั่งนี้ต้องใช้ในเธรดเท่านั้น!", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    thread_name = interaction.channel.name
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nickname_number = extract_number_from_nickname(user.display_name)

    user_points = {user.id: (nickname_number, points, timestamp)}
    update_points_to_sheets(user_points, thread_name, interaction.guild, options=options, transaction_type="deposit")

    embed = discord.Embed(title=f"💎 บวกคะแนน {options.value}", description=f"{user.mention} ได้รับ +{points} {options.value}", color=discord.Color.blue())
    embed.set_footer(text=thread_name)

    summary_channel = send_summary_embed(interaction.guild_id, options)
    if summary_channel:
        await summary_channel.send(embed=embed)
        await interaction.followup.send(f"✅ บวกคะแนนและส่งสรุป {options.value} เรียบร้อยแล้ว!", ephemeral=True)
    else:
        await interaction.followup.send(f"⚠️ ไม่พบห้องสรุป {options.value} ที่ตั้งค่าไว้!", ephemeral=True)

# ✅ ฟังก์ชันถอนคะแนน Bp
@bot.tree.command(name="withdraw_bp", description="หักคะแนน BP ของสมาชิก")
async def withdraw_bp(interaction: discord.Interaction, user: discord.Member, bp: int):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("คำสั่งนี้ต้องใช้ในเธรดเท่านั้น!", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    thread_name = interaction.channel.name
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nickname_number = extract_number_from_nickname(user.display_name if user else user.name)
    user_bp = {user.id: (nickname_number, bp, timestamp)}
    update_points_to_sheets(user_bp, thread_name, interaction.guild, options=PointType.BP, transaction_type="withdraw")
    embed = discord.Embed(title="❌ แจ้งถอน BP", description=f"{user.mention} ถอน {bp} BP",
                          color=discord.Color.red())
    embed.timestamp = datetime.now()

    summary_channel = send_summary_embed(interaction.guild_id, PointType.BP)
    if summary_channel:
        await summary_channel.send(embed=embed)
        await interaction.followup.send(f"✅ หัก {bp} BP จาก {user.mention} แล้ว", ephemeral=True)
    else:
        await interaction.followup.send("⚠️ ไม่พบห้องสรุป BP ที่ตั้งค่าไว้!", ephemeral=True)

# ✅ ฟังก์ชันปันผล WD
# ✅ ฟังก์ชันปันผล WD
@bot.tree.command(name="dividend", description="สร้างเธรดลงทะเบียนปันผล BP หรือ WP")
@app_commands.describe(
    options="เลือกประเภท (BP หรือ WP)",
    room="ห้องที่ใช้สำหรับลงทะเบียน",
    role="โรลที่จะถูกแท็ก",
    deadline="ระยะเวลาการลงทะเบียน (1h, 1d)",
    check="เวลาที่บอทจะเช็คหลังจากปิดเธรด (1h, 1d)"
)
async def dividend(
        interaction: discord.Interaction,
        options: PointType,
        room: discord.TextChannel,
        role: discord.Role,
        deadline: str,
        check: str
):
    await interaction.response.defer(thinking=True, ephemeral=True)  # ป้องกัน Interaction หมดอายุ

    # คำนวณเวลาจาก Deadline และ Check
    time_now = datetime.now(local_tz)
    deadline_delta = convert_to_timedelta(deadline)
    check_delta = convert_to_timedelta(check)

    close_time = time_now + deadline_delta  # เวลาปิดเธรด
    check_time = close_time + check_delta  # เวลาตรวจสอบ
    deadline_str = close_time.strftime("%d/%m/%y %H:%M")

    # เลือก Embed ตามประเภท
    embed_description = (
        f"""📝 วิธีการรับเพชร:
        ・เช็คยอด {options.value} และเพชรได้ที่ห้อง 𝐂𝐡𝐞𝐜𝐤-𝐩𝐨𝐢𝐧𝐭
        ・ลงรูปไอเทมที่เธรดด้านล่าง พร้อมพิมพ์ยอด {options.value}

        📆 ปิดรับการจ่าย-ปิดเปลี่ยนของ: {deadline_str}

        ⚠️ หากไม่ได้ลงรูปภายในช่วงเวลาที่กำหนด ถือว่าสละสิทธิ์
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        📝 How to Receive Diamonds:
        ・Check your {options.value} and diamond balance in the 𝐂𝐡𝐞𝐜𝐤-𝐩𝐨𝐢𝐧𝐭 channel.
        ・Post a picture of your item in the thread below and type your {options.value} amount.

        📆 Payment & Item Exchange Deadline: {deadline_str}

        ⚠️ If you do not submit your picture within the given time, your claim will be forfeited.
        """
    )
    embed = discord.Embed(
        title="📢 รับยอดปันผล (Dividend)",
        description=embed_description,
        color=discord.Color.blue()
    )

    # ส่ง Embed ไปยังห้องที่กำหนด
    msg = await room.send(embed=embed)

    # สร้างเธรดพร้อมวันที่
    current_date = datetime.now().strftime("%d/%m/%Y")
    thread_name = f"💎 ปันผล (Dividend) {options.value} {current_date}"

    thread = await msg.create_thread(name=thread_name, auto_archive_duration=1440)
    await thread.send(f"อย่าลืมตรวจสอบ {options.value} ให้ถูกต้อง ⚠️**ลงแค่รูปและยอด {options.value} เท่านั้น‼**\n "
                      f"Don't forget to check {options.value} correctly.⚠️**Only post the picture and the {options.value} amount‼**\n"
                      f"{role.mention}")

    # ตั้งเวลาแจ้งเตือนก่อนปิดเธรด 1 ชั่วโมง
    warning_time = close_time - timedelta(hours=1)
    bot.loop.create_task(schedule_warning(thread, role, warning_time, close_time))
    # ตั้งเวลาปิดเธรดอัตโนมัติ
    bot.loop.create_task(schedule_thread_close(thread, close_time))
    # ตั้งเวลาตรวจสอบคะแนนหลังจากปิดเธรด
    bot.loop.create_task(schedule_check(thread, check_time, options))

    await interaction.followup.send(f"✅ โพสต์ปันผล {options.value} เรียบร้อย! เช็คที่ {room.mention}", ephemeral=True)


# ฟังก์ชันแจ้งเตือนก่อนปิดเธรด
async def schedule_warning(thread, role, warning_time, close_time):
    await asyncio.sleep((warning_time - datetime.now(local_tz)).total_seconds())
    await thread.send(
        f"⏳ อย่าลืมตั้งของ // เปลี่ยนไอเทม // เช็คยอดให้ถูกต้องกันนะครับ {role.mention}\n** "
        f"เธรดจะปิดในอีก 1 ชั่วโมง (ปิดเวลา {close_time.strftime('%d/%m/%y %H:%M')})**\n\n"
        f"> Don't forget to receive dividends // change items // check the balance correctly.")


# ฟังก์ชันปิดเธรด
async def schedule_thread_close(thread, close_time):
    await asyncio.sleep((close_time - datetime.now(local_tz)).total_seconds())
    await thread.edit(locked=True, archived=True)
    await thread.send("# 🚫 Closed")


# เก็บ Thread ID ที่เคยทำการตรวจสอบแล้ว
checked_threads = set()


async def schedule_check(thread, check_time, options):
    global checked_threads

    # ป้องกันการทำงานซ้ำ
    if thread.id in checked_threads:
        return
    checked_threads.add(thread.id)

    await asyncio.sleep((check_time - datetime.now(local_tz)).total_seconds())

    messages = [msg async for msg in thread.history(limit=100)]
    valid_entries = {}
    failed_entries = []

    for msg in messages:
        if msg.author.bot:
            continue

        passed = False
        if any(str(reaction.emoji) == "✅" for reaction in msg.reactions):
            valid_entries[msg.author.id] = (msg.content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            passed = True
        elif any(str(reaction.emoji) == "❌" for reaction in msg.reactions):
            failed_entries.append(msg.author.id)
            passed = True

        # ถ้าไม่มีการกดอิโมจิเลย ก็ถือว่าไม่ถูกตรวจสอบ
        if not passed:
            continue

    # ส่งข้อมูลไปยัง Google Sheets (ทำทีเดียว)
    if valid_entries:
        update_data = {}
        for user_id, (amount, timestamp) in valid_entries.items():
            try:
                member = await thread.guild.fetch_member(user_id)
            except discord.NotFound:
                member = None
            nickname_or_username = member.display_name if member else "Unknown"

            update_data[user_id] = (nickname_or_username, int(amount), timestamp)

        update_points_to_sheets(update_data, thread.name, thread.guild, options=options, transaction_type="withdraw")

    # ส่ง Embed สรุปผล (ทำทีเดียว)
    summary_channel = bot.get_channel(
        bp_summary_room.get(thread.guild.id) if options == PointType.BP else wp_summary_room.get(thread.guild.id))
    if summary_channel:
        embed = discord.Embed(title=f"📊 Dividend Summary {options.value}\n", color=discord.Color.green())
        embed.add_field(
            name="✅ List received",
            value="\n".join([f"<@{user_id}> ﹕{amount} {options.value}" for user_id, (amount, _) in valid_entries.items()]) if valid_entries else "ไม่มี",
            inline=False
        )
        embed.add_field(
            name="❌ Not verified",
            value="\n".join([f"<@{user_id}>\n" for user_id in failed_entries]) if failed_entries else "ไม่มี",
            inline=False
        )

        await summary_channel.send(embed=embed)

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