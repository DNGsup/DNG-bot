import json
import os
import re  # ✅ ใช้ Regular Expression
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from enumOptions import PointType

# กำหนดตัวแปรฐานข้อมูลให้เป็น dictionary ว่างก่อน
broadcast_channels = {}
# ------------------
bp_summary_room = {} # สำหรับเก็บห้องสรุปคะแนน
bp_data = {} # สำหรับเก็บคะแนน
# ------------------
wp_summary_room = {}
wp_data = {}
# ------------------
giveaway_room = {}  # ห้องสำหรับจัดกิจกรรม
giveaways = {}       # ข้อมูลของกิจกรรม
winner_history = {} # ✅ เก็บจำนวนครั้งที่ผู้ใช้เคยชนะ (ในหน่วยความจำ)
# กำหนดรีแอคชันเริ่มต้น
bp_reactions = {
    "🎫": 1,  # 🎫 เข้าร่วม
    "💖": 1,  # 💖 เข้าร่วมตั้งแต่ต้น
    "👥": 1,  # 👥 เข้าร่วม 10 คนหรือน้อยกว่า
    "⏳": 1,  # ⏳ เวลาพิเศษ
    "🤝": 1,  # 🤝 ช่วยเหลือ
    "👑": 3   # 👑 วีไอพี
}

wp_reactions = {
    "🏰": 1  # 🏰 ดันเจี้ยนโลก
}
# ------------------ extract_number_from_nickname ✅------------------
def extract_number_from_nickname(nickname):
    """ดึงเฉพาะตัวเลข 5 หลักแรกจาก Nickname"""
    match = re.search(r'\d{5}', nickname)  # ✅ ค้นหาเลข 5 หลักแรกที่พบ
    return match.group(0) if match else nickname  # ✅ ถ้ามีเลข 5 หลัก ให้ใช้เลขนั้น ถ้าไม่มีให้ใช้ชื่อเดิม

# ------------------ ตั้งค่า Google Sheets API ✅------------------
def init_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # โหลด Credentials จาก Environment Variables
    credentials_json = os.getenv("GCP_CREDENTIALS")
    if not credentials_json:
        raise ValueError("❌ ไม่พบ GCP_CREDENTIALS ใน Environment Variables")

    creds_dict = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    client = gspread.authorize(creds)

    # เปิดไฟล์ Google Sheets ครั้งเดียว แล้วดึงชีตที่ต้องใช้
    spreadsheet = client.open("Data form DC")
    return {
        "client": client,
        "bp_ledger": spreadsheet.worksheet("BP Ledger"),
        "wd_check": spreadsheet.worksheet("WD Check"),
    }

sheets = init_sheets()

# ------------------ update_points_to_sheets (แก้ไขแล้ว) ------------------
def update_points_to_sheets(data, thread_name, guild, options: PointType, transaction_type="deposit"):
    """
    อัปเดตคะแนน BP ไปยัง "BP Ledger" และ WP ไปยัง "WD Check" ใน Google Sheets
    - No. ดึงจากเลข 5 หลักในชื่อเล่น
    - ข้ามการบันทึก Name และ GR (ปล่อยให้สูตรในชีททำงานเอง)
    - BP บันทึกที่ BP Deposit หรือ BP Withdraw ใน "BP Ledger"
    - WP บันทึกที่ WD Deposit ใน "WD Check"
    """

    # เลือกชีตที่เหมาะสม
    sheet = sheets["bp_ledger"] if options == PointType.BP else sheets["wd_check"]

    # ตรวจสอบว่าหัวตารางมีข้อมูลหรือยัง ถ้ายังให้สร้างหัวข้อใหม่
    if sheet.cell(1, 1).value is None:
        if options == PointType.BP:
            sheet.append_row(["Timestamp", "Thread name", "User ID", "No.", "Name", "GR", "BP Deposit", "BP Withdraw"])
        else:  # WP
            sheet.append_row(["Timestamp", "Thread name", "User ID", "No.", "Name", "WD Deposit", "WD Withdraw"])

    rows = []

    for user_id, (nickname, points, timestamp) in data.items():
        member = guild.get_member(int(user_id)) if guild else None
        display_name = member.display_name if member and member.display_name else nickname
        no_value = extract_number_from_nickname(display_name)

        if options == PointType.BP:
            row = [
                timestamp,  # Timestamp
                str(user_id),  # User ID
                no_value,  # No. (เลข 5 หลัก)
                None,  # Name (ข้ามเพื่อไม่ทับสูตร)
                None,  # GR (ข้ามเพื่อไม่ทับสูตร)
                points if transaction_type == "deposit" else "",  # BP Deposit
                thread_name if transaction_type == "deposit" else "",  # Thread name
                points if transaction_type == "withdraw" else "",  # BP Withdraw
                thread_name if transaction_type == "withdraw" else ""  # Thread name สำหรับ withdraw
            ]
        else:  # WP
            row = [
                timestamp,  # Timestamp
                thread_name,  # Thread name
                str(user_id),  # User ID
                no_value,  # No. (เลข 5 หลัก)
                None,  # Name (ข้ามเพื่อไม่ทับสูตร)
                points if transaction_type == "deposit" else "",  # WD Deposit
                points if transaction_type == "withdraw" else ""  # WD Withdraw
            ]

        rows.append(row)

    # ใช้ append_rows เพื่อเพิ่มข้อมูลลงในชีตที่เลือก (แทนที่ update)
    sheet.append_rows(rows, value_input_option="RAW")
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
# ------------------ update_bp_to_sheets ------------------
