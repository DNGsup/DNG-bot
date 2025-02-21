import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# กำหนดตัวแปรฐานข้อมูลให้เป็น dictionary ว่างก่อน
broadcast_channels = {}
notification_room = {}
notification_role = {}
boss_notifications = {}  # เพิ่มตัวแปรสำหรับจัดการแจ้งเตือนบอส
bp_summary_room = {} # สำหรับเก็บห้องสรุปคะแนน
bp_reactions = {} # สำหรับเก็บคะแนน
bp_data = {} # สำหรับเก็บคะแนน
giveaway_room = {}  # ห้องสำหรับจัดกิจกรรม
giveaways = {}       # ข้อมูลของกิจกรรม
winner_history = {} # ✅ เก็บจำนวนครั้งที่ผู้ใช้เคยชนะ (ในหน่วยความจำ)
# ------------------ ตั้งค่า Google Sheets API ------------------
def init_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # โหลด Credentials จาก Render Environment Variables
    credentials_json = os.getenv("GCP_CREDENTIALS")
    if not credentials_json:
        raise ValueError("❌ ไม่พบ GCP_CREDENTIALS ใน Environment Variables")

    creds_dict = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    client = gspread.authorize(creds)
    return client

client = init_sheets()
sheet = client.open("Data form DC").worksheet("BossPoints")  # ตรวจสอบชื่อชีตให้ตรง
# ------------------
def update_bp_to_sheets(data, thread_name, guild):
    """อัปเดตคะแนน BP ไปยัง Google Sheets โดยระบุชื่อเธรด"""

    # ตั้งค่าหัวตาราง (อยู่ที่แถวที่ 1)
    sheet.update("A1", [["User ID", "Username", "BP", "Thread name"]])

    # แปลงข้อมูลให้เป็น List ของ List
    rows = []
    for user_id, (username, bp) in data.items():
        member = guild.get_member(int(user_id))
        display_name = member.display_name if member else username  # ใช้ชื่อเล่นแทน
        rows.append([str(user_id), display_name, bp, thread_name])

    # อัปเดตลงชีตตั้งแต่แถวที่ 2 เป็นต้นไป
    sheet.append_rows(rows)  # เพิ่มข้อมูลแทนการลบทิ้ง
# ------------------ Broadcast management ------------------
def add_broadcast_channel(guild_id: str, channel_id: int):
    """เพิ่มช่องสำหรับ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    if guild_id not in broadcast_channels:
        broadcast_channels[guild_id] = set()
    broadcast_channels[guild_id].add(channel_id)

def remove_broadcast_channel(guild_id: str, channel_id: int):
    """ลบช่องออกจาก broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    if guild_id in broadcast_channels and channel_id in broadcast_channels[guild_id]:
        broadcast_channels[guild_id].remove(channel_id)
        if not broadcast_channels[guild_id]:
            del broadcast_channels[guild_id]  # ลบ key ถ้าเซิร์ฟเวอร์นั้นไม่มีช่องเหลืออยู่

def get_rooms(guild_id: str):
    """ดึงรายการ channel_id ของ broadcast ในเซิร์ฟเวอร์ที่กำหนด"""
    return list(broadcast_channels.get(guild_id, []))

# ------------------ Notification Room Management ------------------
def set_notification_room(guild_id: str, channel_id: int):
    """กำหนดห้องแจ้งเตือนของบอส"""
    notification_room[guild_id] = channel_id

def get_notification_room(guild_id: str):
    """ดึงห้องแจ้งเตือนของบอส"""
    return notification_room.get(guild_id)

# ------------------ Notification Role Management ------------------
def set_notification_role(guild_id: str, role_id: int):
    """กำหนด role ที่จะถูก mention เมื่อมีการแจ้งเตือน"""
    notification_role[guild_id] = role_id

def get_notification_role(guild_id: str):
    """ดึง role ที่ใช้สำหรับแจ้งเตือน"""
    return notification_role.get(guild_id)